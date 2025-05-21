import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket
import uuid

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and their authentication state.
    """
    
    def __init__(self):
        # Maps connection IDs to WebSocket objects
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Maps connection IDs to authentication tokens
        self.connection_tokens: Dict[str, str] = {}
        
        # Maps connection IDs to client IDs
        self.connection_clients: Dict[str, str] = {}
        
        # Maps client IDs to connection IDs (for multiple connections per client)
        self.client_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Accepts a WebSocket connection and returns a connection ID.
        """
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        logger.info(f"New WebSocket connection: {connection_id}")
        return connection_id
    
    def disconnect(self, connection_id: str):
        """
        Removes a WebSocket connection.
        """
        if connection_id in self.active_connections:
            # Get client ID if it exists
            client_id = self.connection_clients.get(connection_id)
            
            # Remove from active connections
            del self.active_connections[connection_id]
            
            # Remove from connection tokens
            if connection_id in self.connection_tokens:
                del self.connection_tokens[connection_id]
            
            # Remove from connection clients
            if connection_id in self.connection_clients:
                del self.connection_clients[connection_id]
            
            # Remove from client connections
            if client_id and client_id in self.client_connections:
                self.client_connections[client_id].discard(connection_id)
                if not self.client_connections[client_id]:
                    del self.client_connections[client_id]
            
            logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Any):
        """
        Sends a message to a specific connection.
        """
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_json(message)
            logger.debug(f"Message sent to connection {connection_id}")
    
    async def broadcast(self, message: Any):
        """
        Broadcasts a message to all connections.
        """
        for connection_id, websocket in self.active_connections.items():
            await websocket.send_json(message)
        logger.debug(f"Message broadcast to {len(self.active_connections)} connections")
    
    def set_token(self, connection_id: str, token: str):
        """
        Associates an authentication token with a connection.
        """
        self.connection_tokens[connection_id] = token
        logger.info(f"Token set for connection {connection_id}")
    
    def get_token(self, connection_id: str) -> Optional[str]:
        """
        Gets the authentication token for a connection.
        """
        return self.connection_tokens.get(connection_id)
    
    def is_authenticated(self, connection_id: str) -> bool:
        """
        Checks if a connection is authenticated.
        """
        return connection_id in self.connection_tokens
    
    def set_client(self, connection_id: str, client_id: str):
        """
        Associates a client ID with a connection.
        """
        self.connection_clients[connection_id] = client_id
        
        # Add to client connections
        if client_id not in self.client_connections:
            self.client_connections[client_id] = set()
        self.client_connections[client_id].add(connection_id)
        
        logger.info(f"Client ID {client_id} set for connection {connection_id}")
    
    def get_client(self, connection_id: str) -> Optional[str]:
        """
        Gets the client ID for a connection.
        """
        return self.connection_clients.get(connection_id)
    
    def get_connections_for_client(self, client_id: str) -> Set[str]:
        """
        Gets all connection IDs for a client ID.
        """
        return self.client_connections.get(client_id, set())
    
    def get_all_connections(self) -> list:
        """
        Get all active connection IDs.
        
        Returns:
            List of connection IDs
        """
        return list(self.active_connections.keys())


# Create a singleton instance
connection_manager = ConnectionManager() 