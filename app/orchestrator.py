from crewai import Crew, Task
from .agents.customer.SolarizationAgent.agent import solarization_helper
from .agents.customer.SolarizationAgent.tasks import solar_provider_selection_task
from models import ChatRequest


class Orchestrator:

    def __init__(self, payload: ChatRequest):
        self.agents = [solarization_helper]
        self.tasks = [solar_provider_selection_task]
        self.payload = payload

    def run(self):
        output = solar_provider_selection_task.execute_sync(
            agent=solarization_helper, context=self.payload.client_id
        )

        return output
