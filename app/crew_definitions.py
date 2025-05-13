from crewai import Agent, Task
from .config import common_llm

researcher_agent = Agent(
    role='Researcher',
    goal='Uncover groundbreaking technologies in {topic}',
    backstory=(
        "You are a renowned researcher known for your ability to spot emerging trends "
        "and technologies. You have a keen eye for detail and a passion for innovation."
    ),
    llm=common_llm,
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

# You can define more agents and tasks here as needed.
