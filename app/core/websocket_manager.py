import logging
from typing import Dict, Any, List, Optional
from fastapi import WebSocket
import uuid
import asyncio
import time

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages WebSocket connections.
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_connections: Dict[str, str] = {}  # Maps client_id to connection_id
        self.connection_tokens: Dict[str, str] = {}  # Maps connection_id to token
        self.meter_connections = {}
    
    async def connect(self, websocket: WebSocket) -> str:
        """
        Connect a new WebSocket and return a unique connection ID.
        """
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        logger.info(f"New WebSocket connection: {connection_id}")
        return connection_id
    
    def set_client(self, connection_id: str, client_id: str):
        """
        Associate a client ID with a connection ID.
        """
        self.client_connections[client_id] = connection_id
        logger.info(f"Client ID {client_id} set for connection {connection_id}")
    
    def get_client(self, connection_id: str) -> Optional[str]:
        """
        Get the client ID associated with a connection ID.
        """
        for client_id, conn_id in self.client_connections.items():
            if conn_id == connection_id:
                return client_id
        return None
    
    def get_connection(self, client_id: str) -> Optional[str]:
        """
        Get the connection ID for a client ID.
        """
        return self.client_connections.get(client_id)
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect a client and clean up resources.
        """
        # Find and remove any meter ID mappings for this connection
        meter_ids_to_remove = []
        for meter_id, conn_id in self.meter_connections.items():
            if conn_id == connection_id:
                meter_ids_to_remove.append(meter_id)
        
        for meter_id in meter_ids_to_remove:
            del self.meter_connections[meter_id]
        
        # Existing disconnect logic
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.client_connections:
            del self.client_connections[connection_id]
        if connection_id in self.connection_tokens:
            del self.connection_tokens[connection_id]
        logger.info(f"Client disconnected: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: The connection ID
            message: The message to send
            
        Returns:
            True if the message was sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found")
            return False
        
        websocket = self.active_connections[connection_id]
        
        try:
            # Make sure the message has a status field if it doesn't already
            if "status" not in message and message.get("type") == "grid_alert":
                message["status"] = "success"
                
            await websocket.send_json(message)
            logger.debug(f"Message sent to connection {connection_id}")
            return True
        except RuntimeError as e:
            if "Cannot call 'send' once a close message has been sent" in str(e):
                logger.info(f"Connection {connection_id} is closed, removing from active connections")
                # Remove the closed connection from the active connections
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
                # Also remove any client association
                for client_id, conn_id in list(self.client_connections.items()):
                    if conn_id == connection_id:
                        del self.client_connections[client_id]
            else:
                logger.error(f"Error sending message to connection {connection_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {str(e)}")
            return False
    
    async def broadcast(self, message: Any):
        """
        Broadcast a message to all connected clients.
        """
        for connection_id in list(self.active_connections.keys()):
            await self.send_message(connection_id, message)
    
    async def send_to_client(self, client_id: str, message: Any) -> bool:
        """
        Send a message to a specific client.
        
        Returns:
            True if the message was sent, False otherwise
        """
        connection_id = self.client_connections.get(client_id)
        if not connection_id:
            logger.warning(f"No connection found for client {client_id}")
            return False
        
        return await self.send_message(connection_id, message)
    
    def get_all_connections(self) -> List[str]:
        """
        Get all active connection IDs.
        """
        return list(self.active_connections.keys())
    
    async def start_cleanup_task(self):
        """Start a background task to clean up stale connections."""
        asyncio.create_task(self._cleanup_stale_connections())
    
    async def _cleanup_stale_connections(self):
        """Periodically clean up stale connections."""
        while True:
            try:
                # Sleep for 5 minutes
                await asyncio.sleep(300)
                
                # Check each connection
                for connection_id in list(self.active_connections.keys()):
                    # Try to ping the connection
                    try:
                        websocket = self.active_connections[connection_id]
                        # Send a ping message
                        await websocket.send_json({
                            "type": "ping",
                            "status": "success",
                            "timestamp": time.time()
                        })
                    except Exception:
                        # If there's an error, remove the connection
                        logger.info(f"Removing stale connection {connection_id}")
                        if connection_id in self.active_connections:
                            del self.active_connections[connection_id]
                        # Also remove any client association
                        for client_id, conn_id in list(self.client_connections.items()):
                            if conn_id == connection_id:
                                del self.client_connections[client_id]
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")

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

    def set_meter_id(self, connection_id: str, meter_id: str):
        """
        Associate a meter ID with a connection ID.
        """
        self.meter_connections[meter_id] = connection_id
        logger.info(f"Associated meter ID {meter_id} with connection ID {connection_id}")

    def get_connection_by_meter_id(self, meter_id: str) -> Optional[str]:
        """
        Get the connection ID associated with a meter ID.
        """
        return self.meter_connections.get(meter_id)

# Create a singleton instance
connection_manager = WebSocketManager() 