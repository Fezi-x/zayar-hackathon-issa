from sqlalchemy.orm import Session
from app.repositories.prompt_repo import PromptRepository
from app.repositories.message_repo import MessageRepository
from app.services.groq_provider import LLMClient


class GeneratorService:
    def __init__(self, db: Session):
        self.db = db
        self.prompt_repo = PromptRepository(db)
        self.message_repo = MessageRepository(db)
        self.llm_client = LLMClient()

    async def generate(self, session_id: str, user_content: str, history_limit: int = 10):
        # 1. Save user message
        self.message_repo.create_message(session_id=session_id, role="user", content=user_content)

        # 2. Fetch active prompt with fail-safe fallback
        active_prompt = self.prompt_repo.get_active_prompt()
        
        # Fallback to latest prompt if no active one found
        if not active_prompt:
            active_prompt = self.db.query(Prompt).order_by(Prompt.version.desc()).first()
            
        if not active_prompt:
            raise ValueError("Zero prompts found in database. Initialization required.")

        # 3. Fetch history
        history = self.message_repo.get_last_n_messages(history_limit)
        # Reverse to chronological
        history.reverse()

        # 4. Build LLM messages
        llm_messages = [{"role": "system", "content": active_prompt.content}]
        # Note: History includes the message we just saved. 
        # But we want to avoid double-adding if we use the last N.
        # Let's just use the history as is, since it contains the user message.
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # 5. Call LLM
        reply = await self.llm_client.chat(messages=llm_messages)

        # 6. Save assistant reply
        self.message_repo.create_message(
            session_id=session_id,
            role="assistant", 
            content=reply, 
            prompt_version_id=active_prompt.id
        )

        return reply
