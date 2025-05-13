from crewai.tools import tool

@tool
def get_location(id: str) -> str:
    """
    Fetches the location of the user based on their ID.
    """
    return "Singapore"
