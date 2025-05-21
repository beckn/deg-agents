from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import Dict, Any, Optional, List
import logging
import json
import uuid
import asyncio
import random
from app.core.websocket_manager import connection_manager
from app.core.orchestrator import ClientOrchestrator
from app.core.history_manager import chat_history_manager
from app.utils.model_warmer import warm_up_model

logger = logging.getLogger(__name__)

router = APIRouter(tags=["grid_utility"])

# Add a dictionary to store transformer data for each client
transformer_data_store: Dict[str, Dict[str, Any]] = {}

@router.websocket("/grid-utility/ws")
async def grid_utility_websocket_endpoint(websocket: WebSocket, background_tasks: BackgroundTasks):
    """
    WebSocket endpoint for grid-utility chat.
    No authentication required.
    """
    connection_id = None
    try:
        # Start model warming in the background
        background_tasks.add_task(warm_up_model)
        
        # Let the connection manager accept the connection
        connection_id = await connection_manager.connect(websocket)
        
        # Generate a unique client_id for this connection if needed
        default_client_id = f"grid_client_{str(uuid.uuid4())[:8]}"
        
        logger.info(f"Grid-Utility WebSocket connection established, connection ID: {connection_id}")
        
        # Send acknowledgment to client
        await connection_manager.send_message(
            connection_id,
            {
                "status": "connected",
                "connection_id": connection_id,
                "message": "Grid-Utility connection established. Model warming up in background."
            }
        )
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse message
                message_data = json.loads(data)
                
                # Extract client_id and query
                client_id = message_data.get("client_id", default_client_id)
                query = message_data.get("query")
                
                if not query:
                    await connection_manager.send_message(
                        connection_id,
                        {"status": "error", "message": "query is required"}
                    )
                    continue
                
                # Associate client ID with connection
                connection_manager.set_client(connection_id, client_id)
                
                # Process the query directly without authentication
                await process_grid_utility_query(connection_id, client_id, query)
                
            except json.JSONDecodeError:
                await connection_manager.send_message(
                    connection_id,
                    {"status": "error", "message": "Invalid JSON format"}
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await connection_manager.send_message(
                    connection_id,
                    {"status": "error", "message": f"An error occurred: {str(e)}"}
                )
    
    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id)


async def process_grid_utility_query(connection_id: str, client_id: str, query: str):
    """
    Processes a grid-utility query over WebSocket without authentication.
    """
    logger.info(f"Client {client_id} - Processing grid-utility query")
    
    try:
        # Check if this is a response to a DFP recommendation
        if client_id in transformer_data_store and query.lower() in ["yes", "yes, proceed", "proceed", "ok", "activate"]:
            # Admin has approved the DFP activation
            await activate_dfp(connection_id, client_id)
            return
        
        # Regular query processing (existing code)
        # Get or create the orchestrator instance for this client
        orchestrator = ClientOrchestrator.get_instance(client_id)
        
        # Override the route to always use grid_utility
        # This ensures the query goes to the grid-utility handler regardless of content
        route_key = "grid_utility"
        
        # For complex queries, send an immediate acknowledgment
        await connection_manager.send_message(
            connection_id,
            {
                "status": "processing",
                "query": query,
                "client_id": client_id,
                "message": "Processing your grid-utility query..."
            }
        )
        
        # Process the query with the specific handler
        handler_config_name = None
        for route_cfg in orchestrator.app_config.query_router.routes:
            if route_cfg.route_key == route_key:
                handler_config_name = route_cfg.handler_config_name
                break
        
        if not handler_config_name:
            raise ValueError(f"No handler configuration found for route key: {route_key}")
        
        query_handler = orchestrator._get_handler(handler_config_name)
        
        # Add user query to history
        orchestrator.history_manager.add_user_message(client_id, query)
        current_chat_history = orchestrator.history_manager.get_history(client_id)
        
        # Process the query with the handler
        ai_message = await query_handler.handle_query(query, current_chat_history)
        
        # Add AI response to history
        orchestrator.history_manager.add_ai_message(client_id, ai_message)
        
        # Send the final response
        await connection_manager.send_message(
            connection_id,
            {
                "status": "success",
                "query": query,
                "client_id": client_id,
                "message": ai_message
            }
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred for client {client_id}: {e}")
        await connection_manager.send_message(
            connection_id,
            {
                "status": "error",
                "message": f"An internal server error occurred: {str(e)}"
            }
        )


# Add this function to handle DFP activation
async def activate_dfp(connection_id: str, client_id: str):
    """
    Activates the recommended DFP option.
    """
    logger.info(f"Activating DFP for client {client_id}")
    
    # Get transformer data
    transformer_data = transformer_data_store.get(client_id, {})
    if not transformer_data:
        await connection_manager.send_message(
            connection_id,
            {
                "type": "error",
                "status": "error",
                "client_id": client_id,
                "message": "No active transformer alert found."
            }
        )
        return
    
    # Send activation message
    await connection_manager.send_message(
        connection_id,
        {
            "type": "dfp_activation",
            "status": "success",
            "client_id": client_id,
            "message": "✅ Proceeding to Activate Demand Flexibility Option 1 – Dynamic Demand Response (DDR). Please wait…"
        }
    )
    
    # Simulate processing delay
    await asyncio.sleep(3)
    
    # Generate a random number of households (between 30 and 60)
    households = random.randint(30, 60)
    
    # Send participation message
    await connection_manager.send_message(
        connection_id,
        {
            "type": "dfp_participation",
            "status": "success",
            "client_id": client_id,
            "message": f"✅ {households} DER-enabled households have participated in DDR."
        }
    )
    
    # Simulate another delay
    await asyncio.sleep(2)
    
    # Send success message
    transformer_id = transformer_data.get("display_id", "Unknown")
    await connection_manager.send_message(
        connection_id,
        {
            "type": "dfp_success",
            "status": "success",
            "client_id": client_id,
            "message": f"✔️ Central Feeder Hub [{transformer_id}] load is now back to normal."
        }
    )
    
    # Clear transformer data for this client
    if client_id in transformer_data_store:
        del transformer_data_store[client_id] 