from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.prompt import Prompt


class PromptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_prompt(self) -> Optional[Prompt]:
        return self.db.query(Prompt).filter(Prompt.is_active == True).order_by(Prompt.version.desc()).first()

    def create_prompt(self, version: int, content: str, is_active: bool, triggered_by: str = "manual") -> Prompt:
        db_prompt = Prompt(
            version=version,
            content=content,
            is_active=is_active,
            triggered_by=triggered_by
        )
        self.db.add(db_prompt)
        self.db.commit()
        self.db.refresh(db_prompt)
        return db_prompt

    def activate_prompt(self, prompt_id: str):
        self.db.query(Prompt).update({Prompt.is_active: False})
        self.db.query(Prompt).filter(Prompt.id == prompt_id).update({Prompt.is_active: True})
        self.db.commit()

    def get_latest_version(self) -> int:
        latest = self.db.query(func.max(Prompt.version)).scalar()
        return latest if latest is not None else 0

    def get_by_id(self, prompt_id: str) -> Optional[Prompt]:
        return self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
