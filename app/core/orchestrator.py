from typing import Dict, Optional
import requests
import random
from app.config.settings import settings, AppConfig, HandlerConfig
from app.core.history_manager import chat_history_manager
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
        self.er_id = self._create_meter_and_er()
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

    async def process_query(self, query: str, is_utility: bool = False) -> str:
        """
        Main method to process a user's query.
        1. Adds user query to history.
        2. If is_utility is True, directly select UtilityHandler.
        3. Else, routes the query.
        4. Gets/Initializes the appropriate handler.
        5. Handler processes the query.
        6. Adds AI response to history.
        7. Returns AI response.
        """
        # 1. Add user query to history
        self.history_manager.add_user_message(self.client_id, query)
        current_chat_history = self.history_manager.get_history(self.client_id)

        handler_config_name: Optional[str] = None

        if is_utility:
            utility_handler_key = "utility_query_handler"
            if utility_handler_key in self.app_config.handlers:
                handler_config_name = utility_handler_key
                print(
                    f"Client '{self.client_id}': Query is a utility query, directly using '{handler_config_name}'"
                )
            else:

                error_msg = f"Utility handler '{utility_handler_key}' not configured for client '{self.client_id}'. Cannot process utility query."
                print(f"Error: {error_msg}")
                ai_response = "I'm sorry, I'm not configured to handle this utility request at the moment."
                self.history_manager.add_ai_message(self.client_id, ai_response)
                return ai_response
        else:
            # 2. Route the query (original logic if not a utility query)
            # Pass history to router if it's configured to use it
            route_key = await self.query_router.route_query(query, current_chat_history)
            print(f"Client '{self.client_id}': Query routed to '{route_key}'")

            # Find the handler config name associated with this route_key
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
                    # No handlers configured at all
                    ai_response = "I'm sorry, but I'm not configured to handle any queries at the moment, and no default handler is available."
                    self.history_manager.add_ai_message(self.client_id, ai_response)
                    return ai_response

        # Ensure handler_config_name is set if we reach here (either by utility or routing)
        if not handler_config_name:
            # This case should ideally be caught by the logic above,
            # but as a safeguard:
            print(
                f"Internal Error: Could not determine handler for client '{self.client_id}' for query: {query}"
            )
            ai_response = "I'm sorry, an internal error occurred, and I could not determine how to handle your request."
            self.history_manager.add_ai_message(self.client_id, ai_response)
            return ai_response

        # 3. Get/Initialize the appropriate handler
        try:
            query_handler = self._get_handler(handler_config_name)
        except Exception as e:
            print(
                f"Error obtaining handler '{handler_config_name}' for client '{self.client_id}': {e}"
            )
            ai_response = f"I'm sorry, there was an issue setting up the appropriate assistant for your query: {e}"
            self.history_manager.add_ai_message(self.client_id, ai_response)
            return ai_response

        # 4. Handler processes the query
        try:
            ai_response = await query_handler.handle_query(query, current_chat_history)
        except Exception as e:
            print(
                f"Error during query handling by '{handler_config_name}' for client '{self.client_id}': {e}"
            )
            ai_response = f"I encountered an error trying to process your request with the {handler_config_name.replace('_', ' ')}. Please try again."
            self.history_manager.add_ai_message(self.client_id, ai_response)

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

    def _create_meter_and_er(self):
        """Creates a meter and er for the client."""
        meter_id = None
        retries = 5  # Max retries for creating a unique meter

        for attempt in range(retries):
            random_three_digit_number = random.randint(100, 999)
            meter_code = f"METER{random_three_digit_number}"
            meter_payload = {
                "data": {
                    "code": meter_code,
                    "parent": None,
                    "energyResource": None,
                    "consumptionLoadFactor": 1.0,
                    "productionLoadFactor": 0.0,
                    "type": "SMART",
                    "city": "San Francisco",
                    "state": "California",
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "pincode": "94103",
                }
            }
            meter_url = (
                "https://playground.becknprotocol.io/meter-data-simulator/meters"
            )
            headers = {"Content-Type": "application/json"}

            try:
                print(
                    f"Attempt {attempt + 1}: Creating meter with code {meter_code} for client {self.client_id}"
                )
                response = requests.post(
                    meter_url, json=meter_payload, headers=headers, timeout=10
                )
                response.raise_for_status()  # Raise an exception for HTTP errors
                response_data = response.json()

                if response_data.get(
                    "message"
                ) == "Meter created successfully" and response_data.get("data"):
                    meter_id = response_data["data"].get("id")
                    if meter_id:
                        print(
                            f"Meter created successfully with ID: {meter_id} for client {self.client_id}"
                        )
                        break  # Exit loop if meter creation is successful
                elif (
                    response_data.get("error")
                    and response_data["error"].get("message")
                    == "This attribute must be unique"
                ):
                    print(
                        f"Meter code {meter_code} already exists. Retrying... ({attempt + 1}/{retries})"
                    )
                    continue
                else:
                    print(f"Unexpected response during meter creation: {response_data}")
                    # Potentially raise an error or handle differently

            except requests.exceptions.RequestException as e:
                print(f"Error creating meter for client {self.client_id}: {e}")
                # Depending on the error, you might want to retry or raise
                if attempt == retries - 1:  # If it's the last attempt
                    raise Exception(
                        f"Failed to create meter after {retries} attempts: {e}"
                    )
            except Exception as e:
                print(f"An unexpected error occurred during meter creation: {e}")
                if attempt == retries - 1:
                    raise Exception(
                        f"Failed to create meter after {retries} attempts due to an unexpected error: {e}"
                    )

        if not meter_id:
            error_msg = f"Failed to create a unique meter for client {self.client_id} after {retries} attempts."
            print(error_msg)
            raise Exception(error_msg)

        # Step 2: Create Energy Resource
        er_name = f"Client_{self.client_id}_Resource_{random.randint(100,999)}"  # Adding some randomness to ER name as well
        er_payload = {
            "data": {
                "name": er_name,
                "type": "CONSUMER",
                "meter": meter_id,
            }
        }
        er_url = (
            "https://playground.becknprotocol.io/meter-data-simulator/energy-resources"
        )

        try:
            print(
                f"Creating energy resource '{er_name}' linked to meter ID {meter_id} for client {self.client_id}"
            )
            response = requests.post(
                er_url, json=er_payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            er_response_data = response.json()

            if er_response_data.get(
                "message"
            ) == "Energy resource created successfully" and er_response_data.get(
                "data"
            ):
                er_id = er_response_data["data"].get("id")
                if er_id:
                    print(
                        f"Energy resource created successfully with ID: {er_id} for client {self.client_id}"
                    )
                    return er_id
                else:
                    raise Exception(
                        f"Energy resource created but ID not found in response for client {self.client_id}: {er_response_data}"
                    )
            else:
                raise Exception(
                    f"Failed to create energy resource for client {self.client_id}. Response: {er_response_data}"
                )

        except requests.exceptions.RequestException as e:
            print(f"Error creating energy resource for client {self.client_id}: {e}")
            raise Exception(f"Failed to create energy resource: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during energy resource creation: {e}")
            raise Exception(
                f"Failed to create energy resource due to an unexpected error: {e}"
            )
