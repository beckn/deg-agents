from fastapi import FastAPI

app = FastAPI(
    title="CrewAI FastAPI Server",
    description="A FastAPI server to manage CrewAI tasks.",
    version="0.1.0",
)

@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}

from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
class CrewTaskRequest(BaseModel):
    topic: str
    question: str

researcher_agent = Agent(
    role='Researcher',
    goal='Uncover groundbreaking technologies in {topic}',
    backstory=(
        "You are a renowned researcher known for your ability to spot emerging trends "
        "and technologies. You have a keen eye for detail and a passion for innovation."
    ),
    verbose=True,
    allow_delegation=False
)

research_task = Task(
    description=(
        "Identify the top 3 cutting-edge technologies related to {topic}. "
        "For each technology, provide a brief explanation and its potential impact. "
        "Your final answer MUST be a concise summary of these findings. "
        "Focus on answering the question: {question}"
    ),
    expected_output='A bullet list of the top 3 technologies, each with a brief explanation and potential impact.',
    agent=researcher_agent
)

@app.post("/crew/run", tags=["crew"], response_model=dict)
async def run_crew_task(request: CrewTaskRequest) -> dict:
    """
    Runs a CrewAI task with a simple researcher agent.
    """
    # Create the crew
    crew = Crew(
        agents=[researcher_agent],
        tasks=[research_task],
        process=Process.sequential,
        verbose=2
    )
    inputs = {"topic": request.topic, "question": request.question}
    result = crew.kickoff(inputs=inputs)
    
    return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
