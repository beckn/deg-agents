import os
from crewai.llm import LLM

# Ensure your .env file has: MODEL=google/your-chosen-gemini-model (e.g., google/gemini-1.5-pro-latest)
MODEL_NAME = os.getenv("MODEL", "google/gemini-1.5-pro-latest")

common_llm = LLM(
    model=MODEL_NAME,
    # You can add other parameters like temperature if needed, e.g., temperature=0.7
    # Example: temperature=float(os.getenv("LLM_TEMPERATURE", 0.7))
)
