from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str


from typing import Optional


class ChatResponse(BaseModel):
    reply: str
    prompt_version: Optional[int] = 1
    prompt_preview: Optional[str] = ""
