from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import os
from typing import List, Dict, Any

from app.openapi_parser import load_openapi_spec, extract_endpoints_from_spec
from app.tool_registry import ToolRegistry
from app.agent import ChatAgent

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DEG Agent Chatbot",
    description="A FastAPI application for a chatbot agent with dynamically loaded tools from OpenAPI specs.",
    version="0.1.0",
)

# Global variables for agent and tools, initialized at startup
tool_registry_instance: ToolRegistry
chat_agent_instance: ChatAgent

# --- Configuration for OpenAPI Specs ---
# Assuming specs are in a 'specs' directory relative to the project root
# The user's workspace is /home/aquila/Desktop/CODE/deg-agents
# So, specs path will be /home/aquila/Desktop/CODE/deg-agents/specs/
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)  # This should give deg-agents
SPECS_DIR = os.path.join(PROJECT_ROOT, "specs")

AVAILABLE_SPECS = {
    "sandbox": os.path.join(SPECS_DIR, "sandbox_api_spec.json"),
    "world_engine": os.path.join(SPECS_DIR, "world_engine_api_spec.json"),
}


# --- Pydantic Models ---
class ChatRequest(BaseModel):
    query: str
    client_id: str


class ChatResponse(BaseModel):
    response: str
    history: List[Dict[str, str]]  # To also return the current session's history


# --- FastAPI Events ---
@app.on_event("startup")
async def startup_event():
    global tool_registry_instance, chat_agent_instance

    logger.info("FastAPI application startup...")
    tool_registry_instance = ToolRegistry()

    for spec_name, spec_path in AVAILABLE_SPECS.items():
        logger.info(f"Loading OpenAPI spec: {spec_name} from {spec_path}")
        try:
            if not os.path.exists(spec_path):
                logger.error(
                    f"Spec file not found: {spec_path}. Please ensure it exists."
                )
                # You might want to raise an error here or handle it gracefully
                continue

            spec_data = load_openapi_spec(spec_path)
            endpoints = extract_endpoints_from_spec(spec_data, spec_name)

            if not endpoints:
                logger.warning(f"No endpoints extracted from spec: {spec_name}")

            for endpoint_info in endpoints:
                tool_registry_instance.register_tool(endpoint_info)
            logger.info(f"Registered {len(endpoints)} tools from {spec_name} spec.")

        except Exception as e:
            logger.error(
                f"Failed to load or process spec {spec_name} from {spec_path}: {e}",
                exc_info=True,
            )
            # Decide if the app should start if a spec fails to load
            # For now, it will continue and log the error.

    if not tool_registry_instance.get_all_tools():
        logger.warning("No tools were loaded. The agent might not be very useful.")
    else:
        logger.info(
            f"Total tools registered: {len(tool_registry_instance.get_all_tools())}"
        )
        # For debugging, list all registered tool names:
        # for tool_name in tool_registry_instance.get_all_tools().keys():
        #     logger.debug(f"Registered tool: {tool_name}")

    chat_agent_instance = ChatAgent(tool_registry_instance)
    logger.info("Chat agent initialized.")
    logger.info("Application startup complete.")


# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not chat_agent_instance:
        logger.error(
            "Chat agent not initialized. This should not happen if startup was successful."
        )
        raise HTTPException(status_code=500, detail="Chat agent not available")

    logger.info(
        f"Received chat request for client_id '{request.client_id}': Query: '{request.query}'"
    )

    agent_response_content = await chat_agent_instance.process_chat(
        request.client_id, request.query
    )
    current_history = chat_agent_instance.chat_histories.get(request.client_id, [])

    return ChatResponse(response=agent_response_content, history=current_history)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the DEG Agent Chatbot. Use the /chat endpoint to interact."
    }


# To run the application (e.g., using uvicorn):
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Ensure you are in the `deg-agents` directory when running this.

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
