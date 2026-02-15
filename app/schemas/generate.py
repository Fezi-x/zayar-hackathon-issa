from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    prompt_version: int
    prompt_preview: str
