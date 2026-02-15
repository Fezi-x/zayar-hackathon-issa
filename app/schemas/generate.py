from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    user_message: str = Field(..., min_length=1)


class GenerateResponse(BaseModel):
    reply: str
    prompt_version: int
