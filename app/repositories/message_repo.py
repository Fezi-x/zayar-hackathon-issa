from typing import List
from sqlalchemy.orm import Session
from app.models.message import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_message(self, role: str, content: str, prompt_version_id: str = None) -> Message:
        db_msg = Message(
            role=role,
            content=content,
            prompt_version_id=prompt_version_id
        )
        self.db.add(db_msg)
        self.db.commit()
        self.db.refresh(db_msg)
        return db_msg

    def get_last_n_messages(self, n: int) -> List[Message]:
        return self.db.query(Message).order_by(Message.created_at.desc()).limit(n).all()

    def clear_all_messages(self):
        self.db.query(Message).delete()
        self.db.commit()
