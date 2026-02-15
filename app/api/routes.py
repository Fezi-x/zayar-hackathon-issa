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
    
    class Config:
        extra = "allow"

class ChatResponse(BaseModel):
    reply: str
    prompt_version: Optional[int] = 1
    prompt_preview: Optional[str] = ""

class EditResponse(BaseModel):
    id: str
    version: int
    content: str

def generate_prompt_preview(content: str, max_length: int = 160) -> str:
    try:
        if not content:
            return ""
        cleaned = " ".join(str(content).split())
        if len(cleaned) <= max_length:
            return cleaned
        return cleaned[:max_length].rstrip() + "..."
    except Exception:
        return ""

import traceback

@router.post("/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        # 1. Generate Response
        service = GeneratorService(db)
        reply = await service.generate(request.session_id, request.message)

        # 2. Autonomous Editor Trigger
        try:
            msg_repo = MessageRepository(db)
            user_msg_count = msg_repo.count_user_messages(request.session_id)
            if user_msg_count > 0 and user_msg_count % 5 == 0:
                editor_service = PromptEditorService(db)
                await editor_service.run_editor(
                    session_id=request.session_id, 
                    triggered_by="autonomous"
                )
        except Exception as e:
            # Silence internal trigger errors to protect user experience
            print(f"Autonomous editor trigger failed: {e}")

        # 3. Metadata Fetching with guaranteed fallbacks
        try:
            prompt_repo = PromptRepository(db)
            active_prompt = prompt_repo.get_active_prompt()
            
            if active_prompt:
                active_content = active_prompt.content or ""
                active_version = active_prompt.version or 1
            else:
                active_content = ""
                active_version = 1
        except Exception:
            active_content = ""
            active_version = 1

        # 4. Success Return with Explicit Casting
        return {
            "reply": str(reply or ""),
            "prompt_version": int(active_version or 1),
            "prompt_preview": str(generate_prompt_preview(active_content or ""))
        }

    except Exception as e:
        print("CHAT ENDPOINT CRITICAL ERROR")
        print(traceback.format_exc())

        # Absolute fallback to prevent 500s
        return {
            "reply": "The system encountered an error. Please try again.",
            "prompt_version": 1,
            "prompt_preview": ""
        }

@router.post("/edit", response_model=EditResponse)
async def edit(db: Session = Depends(get_db)):
    try:
        service = PromptEditorService(db)
        new_prompt = await service.run_editor(triggered_by="manual")
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
