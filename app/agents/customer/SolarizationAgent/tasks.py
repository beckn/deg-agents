from crewai import Task

from .agent import solarization_helper

solar_provider_selection_task = Task(
    description="""
        Assist the user in identifying the most suitable solar panel installation provider based on their geographic location, energy needs, and preferences.
        Steps should include:
        1. Gathering location data and any relevant user preferences
        2. Using the location_tool to filter for qualified and reputable providers
        3. Comparing provider options based on services, pricing, and customer feedback
        4. Presenting the top choices to the user in a clear and concise summary

        Once providers are presented, ask the user if they'd like help initiating contact with a selected provider.
        """,
    expected_output="A list of the top 3 to 5 recommended solar panel installation providers with key comparison points",
    agent=solarization_helper,
    human_input=True,
)
