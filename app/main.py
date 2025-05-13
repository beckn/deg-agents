from fastapi import FastAPI
from crewai import Crew, Process
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from .models import CrewTaskRequest
from .crew_definitions import researcher_agent, research_task

app = FastAPI(
    title="CrewAI FastAPI Server",
    description="A FastAPI server to manage CrewAI tasks, using a modular structure.",
    version="0.1.0",
)

@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/crew/run", tags=["crew"], response_model=dict)
async def run_crew_task(request: CrewTaskRequest) -> dict:
    """
    Runs a CrewAI task using pre-defined agents and tasks.
    The LLM configuration is centralized in app.config.py and used by agents.
    """
    crew = Crew(
        agents=[researcher_agent],
        tasks=[research_task],    
        process=Process.sequential,
        verbose=True 
    )

    inputs = {"topic": request.topic, "question": request.question}
    
    result = crew.kickoff(inputs=inputs)
    
    return {"result": result}


class ChatRequest(BaseModel):
    query: str
    client_id: str

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    pass

# --- End of routes ---

# Comments from original main.py (adjusted)
# common_llm from packages.config.config is used in crew_definitions.researcher_agent
# researcher_agent and research_task are used within this file (app.main)
# CrewTaskRequest is used within this file (app.main)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
