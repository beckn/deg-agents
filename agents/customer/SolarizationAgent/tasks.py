from crewai import Task

from .agent import solarization_helper

research_task = Task(
    description=f"""
        Conduct thorough research on {topic}. Focus on:
        1. Key concepts and definitions
        2. Historical development
        3. Current trends
        4. Future implications
        
        After gathering initial information, check with the human if they want to 
        explore any specific aspect in more detail.
        """,
    expected_output="A comprehensive research document with well-organized sections",
    agent=solarization_helper,
    human_input=True,
)
