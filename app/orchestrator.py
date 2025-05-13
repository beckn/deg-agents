from crewai import Crew, Task
from agents.customer.SolarizationAgent.agent import solarization_agent


class Orchestrator():
    agents = [solarization_agent]

