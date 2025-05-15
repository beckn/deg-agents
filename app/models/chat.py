from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    client_id: str
    is_utility: bool = False


class ChatResponse(BaseModel):
    status: str
    query: str
    client_id: str
    message: str
