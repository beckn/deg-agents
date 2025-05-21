FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

# Install dependencies directly
RUN pip install fastapi uvicorn python-dotenv pyyaml && \
    pip install google-ai-generativelanguage==0.6.2 && \
    pip install google-generativeai==0.5.2 && \
    pip install langchain langchain-openai langchain-google-genai && \
    # Add WebSocket support
    pip install websockets

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]