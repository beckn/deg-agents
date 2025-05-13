# 🚀 CrewAI FastAPI Server

A production-ready FastAPI server designed to manage and execute CrewAI tasks, built with modern Python tooling including UV for package management and Docker for containerization.

**Repository:** [https://github.com/ankitShogun/deg-agents.git](https://github.com/ankitShogun/deg-agents.git)

## ✨ Features

- **🤖 CrewAI Integration**: Run CrewAI agents and tasks via a REST API endpoint.
- **⚡ FastAPI**: High-performance web framework for building APIs.
- **📦 UV Package Management**: Fast and modern Python package installation and locking.
- **🐳 Docker Support**: Containerize the application for easy deployment and scaling.
- **✅ Health Check**: `/health` endpoint for monitoring.

## 🏛️ Project Structure

```
.
├── app/                    # Main FastAPI application
│   ├── __init__.py
│   └── main.py            # Application entry point with FastAPI & CrewAI logic
├── docker/                # Docker configuration
│   ├── docker-compose.yml
│   └── Dockerfile
├── .dockerignore
├── .gitignore
├── .python-version        # Specifies Python version (managed by pyenv/uv)
├── LICENSE
├── mypy.ini               # Mypy configuration (optional, for type checking)
├── pyproject.toml         # Project configuration and dependencies for UV
├── README.md              # This file
└── uv.lock               # UV lock file for reproducible installs
```

## 🚦 Getting Started

### Prerequisites

- Python 3.10+ (as defined in `pyproject.toml` or `.python-version`)
- UV Package Manager
- Docker (for containerized deployment)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ankitShogun/deg-agents.git
    cd deg-agents
    ```

2.  **Install UV (if not already installed):**
    ```bash
    # Recommended way (check https://astral.sh/uv#installation for alternatives)
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Activate UV in your shell if needed
    source $HOME/.cargo/env 
    ```
    *Note: Activation command might differ based on your OS and shell.*

3.  **Create a virtual environment and install dependencies:**
    ```bash
    # Create a virtual environment (recommended)
    uv venv
    # Activate the virtual environment (e.g., on Linux/macOS)
    source .venv/bin/activate 
    # (On Windows use: .venv\Scripts\activate)

    # Install dependencies using uv
    uv pip install -r requirements.txt # Or uv pip sync if using uv.lock directly
    ```
    *Note: Ensure your `pyproject.toml` lists dependencies correctly under `[project.dependencies]`. If you have a `requirements.txt`, use that. If relying solely on `pyproject.toml` and `uv.lock`, `uv pip sync` is preferred.*

### Running Locally

Use the `run.py` script to start the server locally:
```bash
python run.py local
```
This script automatically detects your operating system and directly executes the necessary commands to start the `uvicorn` server from your virtual environment.

The server will be started with auto-reload enabled at `http://localhost:8000`.

If `run.py` encounters issues, or for a more direct approach:
1.  Ensure your virtual environment (`.venv`) is created (`uv venv`) and dependencies are installed (`uv pip sync` or `uv pip install -r requirements.txt`).
2.  Activate the virtual environment:
    -   Windows: `.venv\Scripts\activate`
    -   Linux/macOS: `source .venv/bin/activate`
3.  Run `uvicorn` directly:
    ```bash
    uvicorn app.main:app --host localhost --port 8000 --reload
    ```

## 🐳 Running with Docker

Use the `run.py` script to build and run the application with Docker:
```bash
python run.py docker
```
This script automatically detects your operating system and directly executes `docker compose up --build`, changing to the `docker/` directory if `docker-compose.yml` is located there.

This command will check if Docker is running before proceeding.

If `run.py` encounters issues, or for a more direct approach:
1.  Ensure Docker is running.
2.  Navigate to the directory containing `docker-compose.yml` (usually `docker/`, or the project root if it's there).
    ```bash
    # Example if it's in docker/
    cd docker
    ```
3.  Build and run the container:
    ```bash
    docker compose up --build
    ```
The server will be available at `http://localhost:8000` (or the port mapped in `docker-compose.yml`).

## 🤖 Using the CrewAI Endpoint

Send a POST request to the `/crew/run` endpoint with a JSON body containing `topic` and `question`.

**Example using `curl`:**

```bash
curl -X POST "http://localhost:8000/crew/run" \
     -H "Content-Type: application/json" \
     -d '{
           "topic": "Artificial Intelligence",
           "question": "What are the latest advancements in large language models?"
         }'
```

**Expected Response:**

The endpoint will return a JSON object containing the result from the CrewAI task execution.

```json
{
  "result": "..." // Output from the CrewAI researcher agent
}
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
