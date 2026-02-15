import json
import os
import logging
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from app.repositories.prompt_repo import PromptRepository
from app.repositories.message_repo import MessageRepository
from app.services.groq_provider import LLMClient
from app.models.prompt import Prompt

logger = logging.getLogger(__name__)

class PromptEditorService:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_repo = PromptRepository(db)
        self.message_repo = MessageRepository(db)
        self.llm_client = LLMClient()
        self.max_chars = 8000

    def _apply_payload_guard(self, text: str) -> str:
        if len(text) > self.max_chars:
            logger.warning(f"Payload Guard: Truncating input from {len(text)} to {self.max_chars} characters.")
            return text[-self.max_chars:]
        return text

    def _validate_output(self, content: str):
        forbidden = [
            "Hello", "Welcome", "Please upload", "Our team", 
            "We will review", "Service fee", "I am your", "I'm your",
            "Please feel free", "I look forward", "Let me know"
        ]
        # Check for visa details / checklists (generalized indicators)
        indicators = ["financial", "threshold", "document", "checklist", "procedure"]
        
        lower_content = content.lower()
        for phrase in forbidden:
            if phrase.lower() in lower_content:
                raise ValueError(f"Validation failed: Forbidden phrase '{phrase}' detected.")
        
        # Check for conversational tone indicators
        if any(greet in lower_content for greet in ["hi ", "hey ", "good morning", "good afternoon"]):
            raise ValueError("Validation failed: Conversational tone detected.")

    async def _extract_behavior_report(self, conversations: List[Dict]) -> str:
        """STAGE 1: BEHAVIOR EXTRACTOR"""
        assistant_msgs = []
        for conv in conversations:
            for msg in conv.get("conversation", []):
                if msg.get("direction") == "out":
                    assistant_msgs.append(msg.get("text", ""))
        
        # Limit to last 5 assistant responses
        recent_msgs = assistant_msgs[-5:]
        raw_text = "\n---\n".join(recent_msgs)
        guarded_text = self._apply_payload_guard(raw_text)

        instruction = """# ROLE: BEHAVIOR EXTRACTOR
Extract behavioral patterns from assistant messages.
Ignore user messages.
Summarize patterns only.

# OUTPUT FORMAT:
Behavior Report:
- Tone drift issues
- Hallucinated capabilities
- Over-assumption patterns
- Missing clarification patterns
- Marketing language presence
- Structural formatting weaknesses

Output must be concise (under 1000 tokens)."""

        report = await self.llm_client.generate(
            system_prompt=instruction,
            user_message=f"Assistant Messages:\n{guarded_text}"
        )
        
        # Save report
        report_path = "app/data/behavior_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({"report": report}, f, indent=2)
            
        return report

    async def suggest_improvement(self, history_limit: int = 15):
        # 1. Fetch active prompt
        active_prompt = self.prompt_repo.get_active_prompt()
        if not active_prompt:
            raise ValueError("No active prompt found.")

        # 2. Stage 1: Load and Extract Behavior
        examples_path = "app/data/conversations.json"
        if not os.path.exists(examples_path):
            raise FileNotFoundError(f"Behavioral reference missing: {examples_path}")
        
        with open(examples_path, 'r', encoding='utf-8') as f:
            raw_conversations = json.load(f)
            
        behavior_report = await self._extract_behavior_report(raw_conversations)

        # 3. Stage 2: Rule Improver
        editor_system_prompt = """# ROLE: Senior AI Systems Architect
You are improving a SYSTEM PROMPT by identifying behavioral gaps.
Do NOT generate answers. Edit the RULES only.

# STRICT OUTPUT REQUIREMENTS:
- Be a SYSTEM PROMPT.
- Define identity, constraints, tone, reasoning, scope, and refusal rules.
- DO NOT contain greetings, onboarding, or conversational openings.
- DO NOT include visa details, currency, or document lists.
- Read as internal AI configuration instructions.

Return ONLY the improved SYSTEM PROMPT text. No markdown, no commentary."""

        editor_user_message = f"""# INPUT 1: CURRENT SYSTEM PROMPT
{active_prompt.content}

# INPUT 2: BEHAVIOR REPORT
{behavior_report}

Analyze inputs and reinforce the SYSTEM PROMPT rules."""

        # Truncate user message if needed
        guarded_user_message = self._apply_payload_guard(editor_user_message)

        # Retry logic for Stage 2
        for attempt in range(2):
            try:
                new_content = await self.llm_client.generate(
                    system_prompt=editor_system_prompt,
                    user_message=guarded_user_message
                )
                
                cleaned_content = new_content.strip()
                self._validate_output(cleaned_content)
                
                # Atomic Evolution
                try:
                    self.db.query(Prompt).update({Prompt.is_active: False})
                    latest_v = self.prompt_repo.get_latest_version() or 0
                    new_prompt = self.prompt_repo.create_prompt(
                        version=latest_v + 1,
                        content=cleaned_content,
                        is_active=True
                    )
                    self.db.commit()
                    self.db.refresh(new_prompt)
                    return new_prompt
                except Exception:
                    self.db.rollback()
                    raise
                    
            except ValueError as e:
                logger.warning(f"Editor Stage 2 Validation Failed (Attempt {attempt+1}/2): {e}")
                if attempt == 1:
                    logger.error("System Evolution Aborted: Validation persistent failure.")
                    raise
            except Exception as e:
                logger.error(f"Editor Stage 2 Unexpected Error: {e}")
                raise

        return active_prompt
