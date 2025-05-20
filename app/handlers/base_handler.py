from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from langchain_core.language_models import BaseChatModel
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor  # Or your preferred agent type
from app.config.settings import (
    HandlerConfig,
    LLMConfig,
    ToolConfig,
    settings,
    get_api_key,
)
from app.core.history_manager import ChatHistoryManager, InMemoryChatHistory
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from app.utils.model_warmer import get_warmed_model
import logging
import os

logger = logging.getLogger(__name__)


# Placeholder for dynamic LLM loading
def get_llm_instance(llm_config: LLMConfig) -> BaseChatModel:
    """Creates an LLM instance based on the configuration."""
    api_key = get_api_key(llm_config)
    if llm_config.provider == "openai":
        if not api_key:
            raise ValueError(
                f"API key for OpenAI (env var: {llm_config.api_key_env or 'OPENAI_API_KEY'}) not found."
            )
        return ChatOpenAI(
            model_name=llm_config.model_name,
            temperature=llm_config.temperature,
            openai_api_key=api_key,
            # Add other OpenAI specific parameters from llm_config if any
            # e.g., max_tokens=llm_config.max_tokens
        )
    elif llm_config.provider in ["google", "gemini"]:
        if not api_key:
            raise ValueError(
                f"API key for Google (env var: {llm_config.api_key_env or 'GOOGLE_API_KEY'}) not found."
            )
        return ChatGoogleGenerativeAI(
            model=llm_config.model_name,
            temperature=llm_config.temperature,
            google_api_key=api_key,
        )
    # elif llm_config.provider == "anthropic":
    #     if not api_key:
    #         raise ValueError(f"API key for Anthropic (env var: {llm_config.api_key_env}) not found.")
    #     return ChatAnthropic(model_name=llm_config.model_name, temperature=llm_config.temperature, anthropic_api_key=api_key)
    # Add other providers here
    else:
        raise NotImplementedError(
            f"LLM provider '{llm_config.provider}' is not supported."
        )


class BaseQueryHandler(ABC):
    def __init__(
        self,
        client_id: str,
        handler_config: HandlerConfig,  # Specific config for this handler instance
        global_llm_configs: Dict[str, LLMConfig],
        global_tool_configs: Dict[str, ToolConfig],
        history_manager: ChatHistoryManager,
    ):
        self.client_id = client_id
        self.handler_config = handler_config
        self.history_manager = history_manager

        # Get LLM for this handler
        llm_conf_name = self.handler_config.llm_config_name
        if llm_conf_name not in global_llm_configs:
            raise ValueError(
                f"LLM configuration '{llm_conf_name}' not found for handler."
            )
        self.llm_config = global_llm_configs[llm_conf_name]
        self.llm = get_llm_instance(self.llm_config)

        # Load tools for this handler
        self.tools: List[BaseTool] = self._load_tools(global_tool_configs)

        # Agent (or runnable sequence) specific to this handler
        self.agent_executor: Optional[AgentExecutor] = (
            None  # To be set up by subclasses
        )
        self._setup_agent()

    def _load_tools(self, global_tool_configs: Dict[str, ToolConfig]) -> List[BaseTool]:
        from app.handlers.utils import (
            import_class,
        )  # Local import to avoid circular dependency

        loaded_tools = []
        tool_names_to_load = set(
            self.handler_config.tools.common + self.handler_config.tools.specific
        )

        for tool_name in tool_names_to_load:
            if tool_name not in global_tool_configs:
                print(f"Warning: Tool configuration '{tool_name}' not found. Skipping.")
                continue
            tool_conf = global_tool_configs[tool_name]
            try:
                ToolClass = import_class(tool_conf.class_path)
                # Instantiate the tool. If it has specific args in config, pass them.
                # For now, assume tools are instantiated without extra args from their specific config section.
                # If ToolClass needs config (e.g. API keys for external services not from LLM),
                # you'd pass tool_conf.model_extra or specific fields.
                tool_instance = (
                    ToolClass()
                )  # Example: ToolClass(**tool_conf.model_extra)
                loaded_tools.append(tool_instance)
            except ImportError as e:
                print(
                    f"Error loading tool '{tool_name}' from path '{tool_conf.class_path}': {e}"
                )
            except Exception as e:
                print(f"Error instantiating tool '{tool_name}': {e}")
        return loaded_tools

    def get_chat_history(
        self,
    ) -> InMemoryChatHistory:  # Or BaseChatMessageHistory if you generalize
        return self.history_manager.get_history(self.client_id)

    @abstractmethod
    def _setup_agent(self):
        """
        Subclasses must implement this method to set up their specific
        Langchain agent, chain, or runnable. This will typically involve
        creating a prompt, combining it with the LLM and tools.
        This method should set self.agent_executor (or a similar runnable).
        """
        pass

    @abstractmethod
    async def handle_query(self, query: str, chat_history: InMemoryChatHistory) -> str:
        """
        Processes the user's query using the configured LLM, tools, and history.
        Returns the agent's response.
        """
        pass

    def _setup_llm(self):
        """
        Sets up the LLM based on configuration.
        """
        if self.llm_config.provider.lower() == "google":
            # Try to get a warmed model first
            warmed_model = get_warmed_model()
            
            if warmed_model:
                logger.info(f"Using pre-warmed model")
                # Create a wrapper around the warmed model to match LangChain's interface
                from langchain_google_genai import ChatGoogleGenerativeAI
                
                # Use the pre-warmed model with LangChain
                self.llm = ChatGoogleGenerativeAI(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    google_api_key=os.getenv("GOOGLE_API_KEY"),
                    # Additional configuration...
                )
            else:
                # Fall back to normal initialization
                self.llm = ChatGoogleGenerativeAI(
                    model=self.llm_config.model_name,
                    temperature=self.llm_config.temperature,
                    # Additional configuration...
                )
