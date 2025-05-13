from pydantic import BaseModel

class CrewTaskRequest(BaseModel):
    topic: str
    question: str
