from fastapi import FastAPI
from fastapi import FastAPI

from .models import ChatRequest, ChatResponse

from orchestrator import Orchestrator

app = FastAPI(
    title="CrewAI FastAPI Server",
    description="A FastAPI server to manage CrewAI tasks, using a modular structure.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
