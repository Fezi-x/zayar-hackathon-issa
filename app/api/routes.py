from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.generator_service import GeneratorService
from app.services.prompt_editor import PromptEditorService
from app.repositories.prompt_repo import PromptRepository
from app.repositories.message_repo import MessageRepository
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class ChatRequest(BaseModel):
    session_id: str
    message: str

class EditResponse(BaseModel):
    id: str
    version: int
    content: str

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        service = GeneratorService(db)
        reply = await service.generate(request.message)
        return {"reply": reply}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/edit", response_model=EditResponse)
async def edit(db: Session = Depends(get_db)):
    try:
        service = PromptEditorService(db)
        new_prompt = await service.suggest_improvement()
        return {
            "id": str(new_prompt.id),
            "version": new_prompt.version,
            "content": new_prompt.content
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/activate/{prompt_id}")
async def activate(prompt_id: str, db: Session = Depends(get_db)):
    repo = PromptRepository(db)
    prompt = repo.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    repo.activate_prompt(prompt_id)
    return {"message": f"Prompt V{prompt.version} activated"}

@router.post("/reset")
async def reset(db: Session = Depends(get_db)):
    repo = MessageRepository(db)
    repo.clear_all_messages()
    return {"message": "Conversation history cleared"}
