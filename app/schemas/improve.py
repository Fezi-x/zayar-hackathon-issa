from uuid import UUID
from pydantic import BaseModel, Field


class ImproveRequest(BaseModel):
    generation_id: UUID
    real_reply: str = Field(..., min_length=1)


class ImproveResponse(BaseModel):
    new_prompt_version: int
    activated: bool
