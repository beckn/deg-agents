from typing import Dict, List, Tuple, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

from app.config.settings import settings, QueryRouterConfig, LLMConfig
from app.handlers.base_handler import get_llm_instance  # Re-use LLM instantiation
from app.core.history_manager import InMemoryChatHistory  # or BaseChatMessageHistory


class QueryRouter:
    def __init__(
        self, router_config: QueryRouterConfig, global_llm_configs: Dict[str, LLMConfig]
    ):
        self.router_config = router_config
        llm_conf_name = self.router_config.llm_config_name
        if llm_conf_name not in global_llm_configs:
            raise ValueError(
                f"LLM configuration '{llm_conf_name}' for QueryRouter not found."
            )

        self.llm_config = global_llm_configs[llm_conf_name]
        self.llm = get_llm_instance(self.llm_config)
        self.output_parser = StrOutputParser()
        self.prompt = self._build_routing_prompt()

    def _build_routing_prompt(self) -> ChatPromptTemplate:
        """
        Builds the prompt for the routing LLM.
        The prompt guides the LLM to select one of the predefined route_keys.
        """
        route_descriptions = []
        for route in self.router_config.routes:
            # To make this more dynamic, handler descriptions could come from the handler_config
            # For now, we'll use the route_key and imply its purpose.
            # A more robust approach would be to have a 'description_for_router' field in handler configs.
            handler_conf = settings.handlers.get(route.handler_config_name)
            description = f"'{route.route_key}' for queries related to {handler_conf.class_path.split('.')[-1].replace('QueryHandler', '').lower()} topics."
            if (
                route.route_key == "generic"
            ):  # Special case for a more explicit generic description
                description = f"'{route.route_key}' for general conversation, questions not covered by other categories, or if unsure, especially if the history is empty or irrelevant."
            elif "solar" in route.route_key.lower():
                description = f"'{route.route_key}' for questions specifically about solar panels, solar energy, installation, and related calculations."
            elif "grid" in route.route_key.lower() or "utility" in route.route_key.lower():
                description = f"'{route.route_key}' for questions about electricity grid, utility services, electricity bills, power outages, and utility programs."

            route_descriptions.append(description)

        routing_instructions = (
            "You are an expert at routing a user's query to the correct specialized query handler. "
            "Based on the user's query AND the preceding conversation history (if any), determine which of the following "
            "categories the query falls into. "
            "Only output the category key string (e.g., 'generic', 'solar_installation'). Do NOT add any other text or explanation.\n\n"
            "Available categories:\n"
            + "\n".join(f"- {desc}" for desc in route_descriptions)
            + "\n\nIf the query is a follow-up to a previous topic discussed in the chat history, try to route it to the same handler if appropriate. "
            "If the current query introduces a new topic, route it based on the query's content. "
            "If the query is too ambiguous or doesn't fit any specific category even considering the history, route it to 'generic'."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", routing_instructions),
                MessagesPlaceholder(variable_name="chat_history", optional=True),
                ("human", "User query: {query}\n\nOutput only the category key:"),
            ]
        )
        return prompt

    async def route_query(
        self, query: str, chat_history: Optional[InMemoryChatHistory] = None
    ) -> str:
        """
        Routes the query to the appropriate handler based on LLM classification,
        considering chat history.
        Returns the route_key (e.g., "generic", "solar_installation").
        """
        chain = self.prompt | self.llm | self.output_parser

        history_messages = []
        if chat_history and chat_history.messages:
            history_messages = chat_history.messages
        # Ensure history_messages is always a list, even if empty
        # The MessagesPlaceholder will handle it correctly if it's an empty list.

        result = await chain.ainvoke({"query": query, "chat_history": history_messages})

        # Validate the result against known route_keys
        valid_route_keys = {route.route_key for route in self.router_config.routes}
        cleaned_result = (
            result.strip().lower().replace("'", "").replace('"', "")
        )  # Clean potential LLM artifacts

        if cleaned_result in valid_route_keys:
            return cleaned_result
        else:
            print(
                f"Warning: QueryRouter LLM returned an invalid route_key: '{result}'. Defaulting to 'generic'."
            )
            # Attempt to find a partial match or default
            for key in valid_route_keys:
                if key in cleaned_result:
                    print(f"Found partial match for route_key: '{key}'. Using it.")
                    return key
            return "generic"  # Fallback to a default route if no match
