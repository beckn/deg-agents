from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    client_id: str


class ChatResponse(BaseModel):
    status: str
    query: str
    client_id: str
    message: str
