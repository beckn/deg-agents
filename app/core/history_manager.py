from collections import defaultdict
from typing import List, Dict, Any
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    HumanMessage,
    SystemMessage,
    messages_from_dict,
    messages_to_dict,
)

from app.config.settings import settings  # Import your AppConfig instance


class InMemoryChatHistory(BaseChatMessageHistory):
    """In-memory implementation of chat message history."""

    def __init__(self, client_id: str, max_entries: int = 100):
        self.client_id = client_id
        self.messages: List[BaseMessage] = []
        self.max_entries = max_entries

    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the history."""
        self.messages.append(message)
        # Trim old messages if history exceeds max_entries
        if len(self.messages) > self.max_entries:
            self.messages = self.messages[-self.max_entries :]

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add multiple messages to the history."""
        for message in messages:
            self.add_message(message)

    def clear(self) -> None:
        """Clear the history."""
        self.messages = []

    # Langchain expects these methods
    def add_user_message(self, message: str) -> None:
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        self.add_message(AIMessage(content=message))


class ChatHistoryManager:
    """
    Manages chat histories for different clients.
    Uses the provider specified in the configuration.
    """

    _histories: Dict[str, InMemoryChatHistory] = defaultdict(lambda: None)

    def __init__(self):
        self.config = settings.chat_history
        if self.config.provider != "in_memory":
            # In a real application, you'd initialize other providers here
            # e.g., RedisChatMessageHistory, FileChatMessageHistory, SQLChatMessageHistory
            raise NotImplementedError(
                f"Chat history provider '{self.config.provider}' is not yet implemented."
            )
        self.max_entries_per_client = self.config.max_entries_per_client

    def get_history(self, client_id: str) -> InMemoryChatHistory:
        """
        Retrieves or creates a chat history for a given client_id.
        """
        if client_id not in self._histories:
            self._histories[client_id] = InMemoryChatHistory(
                client_id=client_id, max_entries=self.max_entries_per_client
            )
        return self._histories[client_id]

    def add_message(self, client_id: str, message: BaseMessage):
        history = self.get_history(client_id)
        history.add_message(message)

    def add_user_message(self, client_id: str, query: str):
        history = self.get_history(client_id)
        history.add_user_message(query)

    def add_ai_message(self, client_id: str, response: str):
        history = self.get_history(client_id)
        history.add_ai_message(response)

    def clear_history(self, client_id: str):
        history = self.get_history(client_id)
        history.clear()


# Global instance of the history manager
chat_history_manager = ChatHistoryManager()
