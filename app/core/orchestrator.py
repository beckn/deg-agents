from typing import Dict, Optional
from app.config.settings import settings, AppConfig, HandlerConfig
from app.core.history_manager import (
    ChatHistoryManager,
    chat_history_manager,
)  # Use the global instance
from app.core.query_router import QueryRouter
from app.handlers.base_handler import BaseQueryHandler
from app.handlers.utils import import_class


class ClientOrchestrator:
    """
    Manages the interaction flow for a single client_id.
    Instantiates and holds necessary components like query router and handlers.
    """

    _instances: Dict[str, "ClientOrchestrator"] = (
        {}
    )  # Cache for client-specific orchestrators

    def __init__(self, client_id: str, app_config: AppConfig):
        self.client_id = client_id
        self.app_config = app_config
        self.history_manager = chat_history_manager  # Use the shared history manager

        # Initialize QueryRouter (shared across all clients, so could be outside if stateless)
        # For simplicity here, each orchestrator instance gets its own, but config is shared
        self.query_router = QueryRouter(
            router_config=self.app_config.query_router,
            global_llm_configs=self.app_config.llms,
        )

        # Cache for instantiated handlers for this client
        self.query_handlers: Dict[str, BaseQueryHandler] = {}

    @classmethod
    def get_instance(cls, client_id: str) -> "ClientOrchestrator":
        """
        Factory method to get or create an orchestrator instance for a client_id.
        """
        if client_id not in cls._instances:
            cls._instances[client_id] = cls(client_id=client_id, app_config=settings)
        return cls._instances[client_id]

    def _get_handler(self, handler_config_name: str) -> BaseQueryHandler:
        """
        Retrieves or creates a query handler instance based on its configuration name.
        """
        if handler_config_name in self.query_handlers:
            return self.query_handlers[handler_config_name]

        if handler_config_name not in self.app_config.handlers:
            raise ValueError(
                f"Configuration for handler '{handler_config_name}' not found."
            )

        handler_conf_data: HandlerConfig = self.app_config.handlers[handler_config_name]

        try:
            HandlerClass = import_class(handler_conf_data.class_path)
            handler_instance = HandlerClass(
                client_id=self.client_id,
                handler_config=handler_conf_data,
                global_llm_configs=self.app_config.llms,
                global_tool_configs=self.app_config.tools,
                history_manager=self.history_manager,
            )
            self.query_handlers[handler_config_name] = handler_instance
            return handler_instance
        except ImportError as e:
            print(f"Error importing handler class for '{handler_config_name}': {e}")
            raise
        except Exception as e:
            print(f"Error instantiating handler '{handler_config_name}': {e}")
            raise

    async def process_query(self, query: str) -> str:
        """
        Main method to process a user's query.
        1. Adds user query to history.
        2. Routes the query.
        3. Gets/Initializes the appropriate handler.
        4. Handler processes the query.
        5. Adds AI response to history.
        6. Returns AI response.
        """
        # 1. Add user query to history
        self.history_manager.add_user_message(self.client_id, query)
        current_chat_history = self.history_manager.get_history(self.client_id)

        # 2. Route the query
        # Pass history to router if it's configured to use it
        route_key = await self.query_router.route_query(query, current_chat_history)
        print(f"Client '{self.client_id}': Query routed to '{route_key}'")

        # Find the handler config name associated with this route_key
        handler_config_name: Optional[str] = None
        for route_cfg in self.app_config.query_router.routes:
            if route_cfg.route_key == route_key:
                handler_config_name = route_cfg.handler_config_name
                break

        if not handler_config_name:
            print(
                f"Warning: No handler configured for route_key '{route_key}'. Defaulting to find a generic handler."
            )
            # Try to find a handler named 'generic_query_handler' or the first available one as a fallback
            if "generic_query_handler" in self.app_config.handlers:
                handler_config_name = "generic_query_handler"
            elif self.app_config.handlers:
                handler_config_name = list(self.app_config.handlers.keys())[0]
            else:
                return "I'm sorry, but I'm not configured to handle this type of query, and no default handler is available."

        # 3. Get/Initialize the appropriate handler
        try:
            query_handler = self._get_handler(handler_config_name)
        except Exception as e:
            print(
                f"Error obtaining handler '{handler_config_name}' for client '{self.client_id}': {e}"
            )
            return f"I'm sorry, there was an issue setting up the appropriate assistant for your query: {e}"

        # 4. Handler processes the query
        try:
            ai_response = await query_handler.handle_query(query, current_chat_history)
        except Exception as e:
            print(
                f"Error during query handling by '{handler_config_name}' for client '{self.client_id}': {e}"
            )
            ai_response = f"I encountered an error trying to process your request with the {handler_config_name.replace('_', ' ')}. Please try again."

        # 5. Add AI response to history
        self.history_manager.add_ai_message(self.client_id, ai_response)

        # 6. Return AI response
        return ai_response

    @classmethod
    def clear_client_instance(cls, client_id: str):
        """Removes a client's orchestrator instance from the cache."""
        if client_id in cls._instances:
            del cls._instances[client_id]
            print(f"Cleared orchestrator instance for client_id: {client_id}")

    @classmethod
    def clear_all_client_instances(cls):
        """Clears all cached client orchestrator instances."""
        cls._instances.clear()
        print("Cleared all client orchestrator instances.")
