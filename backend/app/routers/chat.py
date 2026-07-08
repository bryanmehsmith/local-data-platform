from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.clients.pipelines_client import pipelines_client

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: str = "lakehouse_rag"
    history: list[dict] = []


class ChatResponse(BaseModel):
    reply: str
    model: str


@router.post("/completions", response_model=ChatResponse)
def chat_completions(req: ChatRequest):
    try:
        reply = pipelines_client.chat(req.model, req.message, req.history)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Chat backend failed: {e}")
    return ChatResponse(reply=reply, model=req.model)


@router.get("/models")
def list_models():
    return pipelines_client.list_models()
