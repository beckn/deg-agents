from fastapi import APIRouter
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint stub that accepts query and client_id
    """
    return ChatResponse(
        status="received",
        query=request.query,
        client_id=request.client_id,
        message="Chat endpoint is working",
    )
