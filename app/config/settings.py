import yaml
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Define Pydantic models for typed configuration
# These models should reflect the structure of your config.yaml


class LLMConfig(BaseModel):
    provider: str
    model_name: str
    api_key_env: Optional[str] = None  # Env variable name for the API key
    temperature: Optional[float] = 0.7

    # Allow extra fields for provider-specific parameters
    class Config:
        extra = "allow"


class QueryRouterRouteConfig(BaseModel):
    route_key: str
    handler_config_name: str


class QueryRouterConfig(BaseModel):
    llm_config_name: str
    routes: List[QueryRouterRouteConfig]


class HandlerToolConfig(BaseModel):
    common: List[str] = Field(default_factory=list)
    specific: List[str] = Field(default_factory=list)


class HandlerConfig(BaseModel):
    class_path: str
    llm_config_name: str
    tools: HandlerToolConfig

    # Allow extra fields
    class Config:
        extra = "allow"


class ToolConfig(BaseModel):
    class_path: str

    # Allow extra fields for tool-specific parameters
    class Config:
        extra = "allow"


class ChatHistoryConfig(BaseModel):
    provider: str
    max_entries_per_client: Optional[int] = 100  # Example for in_memory

    # Allow extra fields
    class Config:
        extra = "allow"


class AppConfig(BaseModel):
    llms: Dict[str, LLMConfig]
    query_router: QueryRouterConfig
    handlers: Dict[str, HandlerConfig]
    tools: Dict[str, ToolConfig]
    chat_history: ChatHistoryConfig
    # knowledge_bases: Optional[Dict[str, Any]] = None # For future KB stubs


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """Loads the application configuration from a YAML file."""
    # Determine the absolute path to the config file
    # Assuming config.yaml is in the project root, and this script is in app/config/
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    absolute_config_path = os.path.join(project_root, config_path)

    if not os.path.exists(absolute_config_path):
        raise FileNotFoundError(f"Configuration file not found: {absolute_config_path}")

    with open(absolute_config_path, "r") as f:
        config_data = yaml.safe_load(f)
    return AppConfig(**config_data)


# Load the configuration globally
# This instance can be imported by other modules
settings: AppConfig = load_config()


# Helper function to get API keys from environment variables
def get_api_key(llm_config: LLMConfig) -> Optional[str]:
    if llm_config.api_key_env:
        return os.getenv(llm_config.api_key_env)
    # Fallback for common keys if api_key_env is not specified (example)
    if llm_config.provider == "openai":
        return os.getenv("OPENAI_API_KEY")
    return None


if __name__ == "__main__":
    # For testing the configuration loading
    print("Configuration loaded successfully!")
    print("\nLLMs:")
    for name, llm_conf in settings.llms.items():
        print(f"  {name}: {llm_conf.model_dump_json(indent=2)}")
        # Example of getting API key (will be None if not set)
        # api_key = get_api_key(llm_conf)
        # print(f"    API Key (env var {llm_conf.api_key_env}): {'Set' if api_key else 'Not Set'}")

    print("\nQuery Router:")
    print(f"  {settings.query_router.model_dump_json(indent=2)}")

    print("\nHandlers:")
    for name, handler_conf in settings.handlers.items():
        print(f"  {name}: {handler_conf.model_dump_json(indent=2)}")

    print("\nTools:")
    for name, tool_conf in settings.tools.items():
        print(f"  {name}: {tool_conf.model_dump_json(indent=2)}")

    print("\nChat History:")
    print(f"  {settings.chat_history.model_dump_json(indent=2)}")
