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
        
        # Important: Associate the default client ID with this connection immediately
        connection_manager.set_client(connection_id, default_client_id)
        
        logger.info(f"Grid-Utility WebSocket connection established, connection ID: {connection_id}, client ID: {default_client_id}")
        
        # Send acknowledgment to client
        await connection_manager.send_message(
            connection_id,
            {
                "status": "connected",
                "connection_id": connection_id,
                "client_id": default_client_id,  # Include client ID in the response
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
                
                # Check if this is a DFP activation request
                if query.lower().strip() in ["yes", "yes, proceed", "proceed", "activate", "yes, activate"]:
                    await handle_dfp_activation(connection_id, client_id, query)
                else:
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


async def handle_dfp_activation(connection_id: str, client_id: str, query: str):
    """
    Handle a DFP activation request.
    """
    logger.info(f"Client {client_id} - Processing DFP activation request")
    
    try:
        # Get the orchestrator instance for this client
        orchestrator = ClientOrchestrator.get_instance(client_id)
        
        # Add the query to history
        orchestrator.history_manager.add_user_message(client_id, query)
        
        # Get the current chat history
        current_chat_history = orchestrator.history_manager.get_history(client_id)
        
        # Get the handler for grid utility queries
        handler_config_name = None
        for route_cfg in orchestrator.app_config.query_router.routes:
            if route_cfg.route_key == "grid_utility":
                handler_config_name = route_cfg.handler_config_name
                break
        
        if not handler_config_name:
            raise ValueError("No handler configuration found for grid utility queries")
        
        # Get the handler
        query_handler = orchestrator._get_handler(handler_config_name)
        
        # Add client_id to the chat history metadata to ensure it's available to the handler
        if hasattr(current_chat_history, 'messages') and current_chat_history.messages:
            for message in current_chat_history.messages:
                if not hasattr(message, 'metadata'):
                    message.metadata = {}
                message.metadata['client_id'] = client_id
        
        # Log the client's DFP recommendations before processing
        if hasattr(query_handler, 'client_dfp_recommendations'):
            if client_id in query_handler.client_dfp_recommendations:
                recommendation = query_handler.client_dfp_recommendations[client_id]
                option = recommendation.get("option", {})
                transformer = recommendation.get("transformer", {})
                
                logger.info(f"Found DFP recommendation for client {client_id}:")
                logger.info(f"  Option: {option.get('name', 'Unknown')} ({option.get('id', 'Unknown')})")
                logger.info(f"  Transformer: {transformer.get('name', 'Unknown')} [{transformer.get('id', 'Unknown')}]")
                logger.info(f"  Current Load: {transformer.get('current_load', 'Unknown')}")
                logger.info(f"  Load Percentage: {transformer.get('load_percentage', 'Unknown')}%")
                logger.info(f"  Time Estimate: {transformer.get('time_estimate', 'Unknown')} minutes")
            else:
                logger.warning(f"No DFP recommendation found for client {client_id} in handler's client_dfp_recommendations")
        else:
            logger.warning("Handler does not have client_dfp_recommendations attribute")
        
        # Process the query with the handler
        ai_message = await query_handler.handle_query(query, current_chat_history)
        
        # Add AI response to history
        orchestrator.history_manager.add_ai_message(client_id, ai_message)
        
        # Send the initial response
        await connection_manager.send_message(
            connection_id,
            {
                "type": "dfp_activation",
                "status": "success",
                "client_id": client_id,
                "message": ai_message
            }
        )
        
        # HACK: Always proceed with the activation flow, ignoring any error messages
        # Simulate processing delay
        await asyncio.sleep(3)
        
        # Generate a random number of households (between 30 and 60)
        households = random.randint(30, 60)
        
        # Get transformer data or use a default
        transformer_data = transformer_data_store.get(client_id, {"display_id": "TX160"})
        transformer_id = transformer_data.get("display_id", "TX160")
        
        # Send participation message
        # participation_message = f"✅ {households} DER-enabled households have participated in the DFP program."
        # await connection_manager.send_message(
        #     connection_id,
        #     {
        #         "type": "dfp_participation",
        #         "status": "success",
        #         "client_id": client_id,
        #         "message": participation_message
        #     }
        # )
        
        # Add participation message to history
        # orchestrator.history_manager.add_user_message(client_id, f"[SYSTEM ACTION] {participation_message}")
        
        # Simulate another delay
        await asyncio.sleep(2)
        
        # Send success message
        success_message = f"✔️ Central Feeder Hub [{transformer_id}] load is now back to normal."
        # await connection_manager.send_message(
        #     connection_id,
        #     {
        #         "type": "dfp_success",
        #         "status": "success",
        #         "client_id": client_id,
        #         "message": success_message
        #     }
        # )
        
        # Add success message to history
        # orchestrator.history_manager.add_user_message(client_id, f"[SYSTEM ACTION] {success_message}")
        
        # Clear transformer data for this client
        if client_id in transformer_data_store:
            del transformer_data_store[client_id]
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
    
    # Get orchestrator for this client
    orchestrator = ClientOrchestrator.get_instance(client_id)
    
    # Add activation command to history
    orchestrator.history_manager.add_user_message(client_id, "Yes, proceed with the recommended DFP option.")
    
    # Send activation message
    activation_message = "✅ Proceeding to Activate Demand Flexibility Option 1 – Dynamic Demand Response (DDR). Please wait…"
    await connection_manager.send_message(
        connection_id,
        {
            "type": "dfp_activation",
            "status": "success",
            "client_id": client_id,
            "message": activation_message
        }
    )
    
    # Add activation message to history as a user message with a special prefix
    orchestrator.history_manager.add_user_message(client_id, f"[SYSTEM ACTION] {activation_message}")
    
    # Simulate processing delay
    await asyncio.sleep(3)
    
    # Generate a random number of households (between 30 and 60)
    households = random.randint(30, 60)
    
    # Send participation message
    participation_message = f"✅ {households} DER-enabled households have participated in DDR."
    await connection_manager.send_message(
        connection_id,
        {
            "type": "dfp_participation",
            "status": "success",
            "client_id": client_id,
            "message": participation_message
        }
    )
    
    # Add participation message to history
    orchestrator.history_manager.add_user_message(client_id, f"[SYSTEM ACTION] {participation_message}")
    
    # Simulate another delay
    await asyncio.sleep(2)
    
    # Send success message
    transformer_id = transformer_data.get("display_id", "Unknown")
    success_message = f"✔️ Central Feeder Hub [{transformer_id}] load is now back to normal."
    await connection_manager.send_message(
        connection_id,
        {
            "type": "dfp_success",
            "status": "success",
            "client_id": client_id,
            "message": success_message
        }
    )
    
    # Add success message to history
    orchestrator.history_manager.add_user_message(client_id, f"[SYSTEM ACTION] {success_message}")
    
    # Clear transformer data for this client
    if client_id in transformer_data_store:
        del transformer_data_store[client_id] 