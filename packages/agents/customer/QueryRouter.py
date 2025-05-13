# Kept as dummy for now


from crewai.flow import Flow, start, listen
from pydantic import BaseModel


class QueryScope(BaseModel):
    scope: str  # "solarization" or "generic"
    confidence: float
    query: str


class QueryRouterFlow(Flow):
    @start()
    def route_query(self, query: str) -> QueryScope:
        # Use LLM to determine query scope
        # Return QueryScope with scope and confidence
        pass
