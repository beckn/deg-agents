from pydantic import BaseModel


class CrewTaskRequest(BaseModel):
    topic: str
    question: str


class ChatRequest(BaseModel):
    query: str
    client_id: str


class ChatResponse(BaseModel):
    response: str
