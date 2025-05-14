# DEG Agents

## Overview
Endpoints for DEG Agents  
- Consumer Side: Under Development
- Grid Side: Under Planning

This document provides technical details for setting up, running, and understanding the chat query flow of this application.

## Prerequisites
*   **Python**: Version 3.13 (as specified in `.python-version` and `pyproject.toml`). It's recommended to use a Python version manager like `pyenv` to install and manage Python versions.
*   **uv**: This project uses `uv` as its package and virtual environment manager. If you don't have `uv` installed, follow the official installation instructions: [https://github.com/astral-sh/uv#installation](https://github.com/astral-sh/uv#installation)

## Setup and Installation

1.  **Clone the Repository**:
    ```bash
    git clone <your-repository-url>
    cd <your-repository-name>
    ```

2.  **Set up Python 3.13**:
    If using `pyenv` (recommended):
    ```bash
    pyenv install 3.13
    pyenv local 3.13 # Sets the Python version for this project
    ```
    Ensure Python 3.13 is active before proceeding.

3.  **Create Virtual Environment and Install Dependencies using `uv`**:
    `uv` can create the environment and install dependencies in a single step if preferred, or you can do it separately.
    
    To create the environment and activate it:
    ```bash
    uv venv
    source .venv/bin/activate
    ```
    (On Windows, use `.venv\Scripts\activate`)

    Then, install the project dependencies:
    ```bash
    uv pip install -e .
    ```
    This command installs the project in editable mode along with all its dependencies specified in `pyproject.toml`. For development dependencies (like `pylint`, `commitizen`), you can install them using:
    ```bash
    uv pip install -e ".[dev]"
    ```

4.  **Environment Variables**:
    This project uses a `.env` file to manage sensitive information and configurations, such as API keys for Language Models (LLMs).
    *   Create a `.env` file in the root of the project:
        ```bash
        touch .env
        ```
    *   Populate the `.env` file with the necessary environment variables. The required variables, especially API keys for LLMs, are typically referenced in the `config.yaml` file under the `llms:` section (look for `api_key_env` fields).
        For example, if `config.yaml` specifies an LLM like this:
        ```yaml
        # Example snippet from config.yaml
        llms:
          my_openai_llm:
            provider: "openai"
            model_name: "gpt-4"
            api_key_env: "MY_OPENAI_API_KEY"
            temperature: 0.7
        ```
        Your `.env` file should contain:
        ```env
        MY_OPENAI_API_KEY="your_actual_openai_api_key_here"
        ```
        If an `api_key_env` is not specified for an "openai" provider, the system might default to looking for `OPENAI_API_KEY`. Review `app/config/settings.py` and `config.yaml` for precise details on required environment variables.

## Running the Application
Once the setup is complete and the virtual environment is activated, you can run the application using `uv`:
```bash
uv run python3 -m app.main
```
This command executes the `app/main.py` script within the `uv`-managed environment. The `if __name__ == "__main__":` block in `app/main.py` will then start the Uvicorn server.
The server will run with the host, port, and reload settings specified in `app/main.py` (typically `host="0.0.0.0"`, `port=8000`, and `reload=True` for development).

You should see output indicating the server is running, typically `Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)`.

## Chat Query Flow

The application processes chat queries through a structured pipeline orchestrated by the `ClientOrchestrator`. Here's a high-level flow for a single chat query:

1.  **API Request Reception**:
    *   A client sends a `POST` request to the `/chat` endpoint with a JSON body containing `query` (string) and `client_id` (string).

2.  **Request Validation**:
    *   The API layer (FastAPI) validates the incoming request. `query` and `client_id` are mandatory.

3.  **Orchestrator Initialization**:
    *   A `ClientOrchestrator` instance is retrieved or created for the given `client_id`. This allows for managing state and history per client. The orchestrator loads application configurations (LLMs, tools, handlers) from `config.yaml` via `app.config.settings`.

4.  **History Management (User Query)**:
    *   The user's `query` is added to the chat history associated with the `client_id` by the `ChatHistoryManager`.

5.  **Query Routing**:
    *   The `ClientOrchestrator` uses a `QueryRouter` component.
    *   The `QueryRouter` analyzes the `query` (and potentially the current chat history) to determine a `route_key`. This key signifies the type or intent of the query.
    *   The routing logic and criteria are defined in `config.yaml` under the `query_router` section.

6.  **Handler Selection & Initialization**:
    *   Based on the `route_key`, the orchestrator identifies the appropriate `handler_config_name` from the application's configuration.
    *   It then retrieves a cached instance or dynamically imports and instantiates the corresponding query handler class (derived from `BaseQueryHandler`).
    *   Handlers are configured with their specific settings, access to global LLM configurations, tool configurations, and the `ChatHistoryManager`.
    *   If a specific handler isn't found for the route, a fallback (e.g., "generic\_query\_handler") may be used if configured.

7.  **Handler Processing**:
    *   The selected handler's `handle_query(query, current_chat_history)` method is invoked.
    *   This is the core stage where the query is processed. Depending on the handler's implementation, this may involve:
        *   Preparing prompts.
        *   Interacting with one or more Language Models (LLMs).
        *   Utilizing configured tools (if any).
        *   Performing other business logic to generate a response.

8.  **History Management (AI Response)**:
    *   The AI-generated response from the handler is added to the client's chat history by the `ChatHistoryManager`.

9.  **API Response Generation**:
    *   The `ClientOrchestrator` returns the AI message to the API layer.
    *   FastAPI constructs a `ChatResponse` object containing `status`, original `query`, `client_id`, and the AI `message`.

10. **Response to Client**:
    *   The `/chat` endpoint returns the JSON `ChatResponse` to the client with a `200 OK` status if successful. Errors during processing will result in appropriate HTTP error codes and details.

## API Endpoints and Curl Examples

The primary interaction with the chat functionality is via the `/chat` API.

### 1. Process a Chat Query

*   **Endpoint**: `/chat`
*   **Method**: `POST`
*   **Description**: Submits a query for processing and receives a chat response.
*   **Headers**:
    *   `Content-Type: application/json`
*   **Request Body**: `ChatRequest` model
    ```json
    {
        "query": "Your question or message here",
        "client_id": "unique_client_identifier_string"
    }
    ```
    *   `query` (string, required): The user's input/question.
    *   `client_id` (string, required): A unique identifier for the client session. This is used to maintain chat history and context.

*   **Response Body**: `ChatResponse` model (on success, HTTP 200)
    ```json
    {
        "status": "success",
        "query": "Your question or message here",
        "client_id": "unique_client_identifier_string",
        "message": "The AI's response message"
    }
    ```
    *   `status` (string): Indicates the outcome (e.g., "success").
    *   `query` (string): The original query sent by the client.
    *   `client_id` (string): The client ID from the request.
    *   `message` (string): The processed response from the AI/system.

*   **Example `curl` Request**:
    Assuming the server is running on `http://localhost:8000` (default from `app/main.py`):
    ```bash
    curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d '{
        "query": "Hello, how are you today?",
        "client_id": "user123_session456"
    }'
    ```

### 2. Clear Client State (for Debugging/Testing)

*   **Endpoint**: `/chat/{client_id}/clear_state`
*   **Method**: `DELETE`
*   **Description**: Clears the cached orchestrator instance and chat history for a specific `client_id`. This is primarily useful for testing or resetting a client's session.
*   **Path Parameters**:
    *   `client_id` (string, required): The unique identifier for the client whose state needs to be cleared.
*   **Response**:
    *   `204 No Content` on successful clearing.
    *   HTTP errors if the client ID is invalid or an issue occurs.

*   **Example `curl` Request**:
    Replace `user123_session456` with the actual `client_id` you want to clear.
    ```bash
    curl -X DELETE http://localhost:8000/chat/user123_session456/clear_state
    ```

## Configuration (`config.yaml`)

The application's behavior, including LLM providers, query routing, and handler specifics, is heavily driven by the `config.yaml` file located in the project root. Refer to this file and the Pydantic models in `app/config/settings.py` to understand the available configuration options and how to customize them.

## Troubleshooting
*   **Configuration Errors**: If the server fails to start or returns 5xx errors related to configuration, ensure `config.yaml` is correctly formatted and present in the project root. Check that all referenced environment variables (especially API keys) are correctly set in your `.env` file.
*   **Python Version**: Ensure you are using Python 3.13.
*   **Dependencies**: If you encounter import errors, make sure all dependencies are installed correctly within the activated `uv` virtual environment (`uv pip install -e .`).
*   **Port Conflicts**: If port 8000 (default in `app/main.py`) is in use, you can either modify `app/main.py` to use a different port or ensure the port is free.

[YAML Config example](./config.yaml)
