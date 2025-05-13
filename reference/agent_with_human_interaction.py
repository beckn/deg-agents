from crewai import Agent, Task, Crew
from crewai.tools import tool

from dotenv import load_dotenv

load_dotenv()


# Initialize the search tool
@tool
def search_tool(query: str) -> str:
    """
    Performs a search based on a user query.

    Args:
        query: The search query string.

    Returns:
        A string representing the search result.
    """
    # In a real application, this would interact with a search API or database.
    # For this example, we just return a sample string.
    print(
        f"Calling search_tool with query: '{query}'"
    )  # Added print for clarity when simulating
    return f"Sample search result for '{query}'"


# Define our agents
researcher = Agent(
    role="Research Analyst",
    goal="Gather comprehensive information about the given topic",
    backstory="""You are an expert research analyst with years of experience in 
    gathering and analyzing information. You have a keen eye for detail and 
    always ensure your research is thorough and well-documented.""",
    verbose=True,
    tools=[search_tool],
)

analyst = Agent(
    role="Data Analyst",
    goal="Analyze research findings and create meaningful insights",
    backstory="""You are a skilled data analyst who excels at turning raw 
    information into actionable insights. You have a strong background in 
    pattern recognition and trend analysis.""",
    verbose=True,
)

writer = Agent(
    role="Content Writer",
    goal="Create engaging and informative content based on research and analysis",
    backstory="""You are a talented content writer who specializes in making 
    complex information accessible and engaging. You have a gift for storytelling 
    and clear communication.""",
    verbose=True,
)


def get_user_input(prompt):
    """Helper function to get user input"""
    return input(f"\n{prompt}\nYour input: ")


def main():
    # Get topic from user
    topic = get_user_input("Please enter the topic you want to research:")

    # Create tasks with human input enabled
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
        agent=researcher,
        human_input=True,
    )

    analysis_task = Task(
        description="""
        Analyze the research findings and create insights. Consider:
        1. Patterns and trends
        2. Key takeaways
        3. Potential implications
        
        Before finalizing the analysis, check with the human if they want to 
        focus on any particular aspect.
        """,
        expected_output="A detailed analysis report with key insights",
        agent=analyst,
        human_input=True,
    )

    writing_task = Task(
        description="""
        Create an engaging article based on the research and analysis. Ensure:
        1. Clear and accessible language
        2. Logical flow
        3. Engaging narrative
        
        Before finalizing the article, check with the human if they want to 
        emphasize any particular points.
        """,
        expected_output="A well-written article that presents the information clearly",
        agent=writer,
        human_input=True,
    )

    # Create and run the crew
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        verbose=True,
    )

    result = crew.kickoff()
    print("\nFinal Result:")
    print(result)


if __name__ == "__main__":
    main()
