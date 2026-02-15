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

    async def generate(self, user_content: str, history_limit: int = 10):
        # 1. Save user message
        self.message_repo.create_message(role="user", content=user_content)

        # 2. Fetch active prompt with integrity check
        from app.models.prompt import Prompt
        active_count = self.db.query(Prompt).filter_by(is_active=True).count()
        if active_count != 1:
            raise Exception("Integrity error: exactly one active prompt required.")

        active_prompt = self.prompt_repo.get_active_prompt()
        if not active_prompt:
            raise ValueError("No active prompt found. Please create and activate one.")

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
            role="assistant", 
            content=reply, 
            prompt_version_id=active_prompt.id
        )

        return reply
