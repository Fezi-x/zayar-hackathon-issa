import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Text, nullable=False, index=True)
    role = Column(Text, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    prompt_version_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
