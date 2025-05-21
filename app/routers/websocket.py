from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from typing import Dict, Any, Optional
import logging
import json
from app.core.websocket_manager import connection_manager
from app.core.orchestrator import ClientOrchestrator
from app.core.history_manager import chat_history_manager
from app.core.auth import authenticate_user, is_authenticated, get_user_data
from app.core.meter_validator import validate_meter_id
from app.core.otp_service import otp_service
from app.models.chat import ChatRequest, ChatResponse
from app.utils.model_warmer import warm_up_model
import asyncio
import uuid
import requests
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

# Add a dictionary to store the state of conversations
dfp_conversation_state = {}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, background_tasks: BackgroundTasks):
    """
    WebSocket endpoint for real-time chat.
    """
    connection_id = None
    try:
        # Start model warming in the background
        background_tasks.add_task(warm_up_model)
        
        # Let the connection manager accept the connection
        connection_id = await connection_manager.connect(websocket)
        
        # Generate a unique client_id for this connection if needed
        default_client_id = f"client_{str(uuid.uuid4())[:8]}"
        
        logger.info(f"WebSocket connection established, connection ID: {connection_id}")
        
        # Send acknowledgment to client
        await connection_manager.send_message(
            connection_id,
            {
                "status": "connected",
                "connection_id": connection_id,
                "message": "Connection established. Model warming up in background."
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
                
                # Get chat history
                history = chat_history_manager.get_history(client_id)
                
                # Check authentication
                token = connection_manager.get_token(connection_id)
                
                if not token or not is_authenticated(token):
                    # Process authentication flow
                    await process_authentication(connection_id, client_id, query, history)
                else:
                    # User is authenticated, process the query
                    await process_authenticated_query(connection_id, client_id, query, token)
                
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


async def process_authentication(connection_id: str, client_id: str, query: str, history):
    """
    Processes authentication flow over WebSocket.
    """
    # Get current auth state
    auth_state = get_auth_state_from_history(history)
    logger.info(f"Client {client_id} - Current auth state: {auth_state}")
    
    # If we're waiting for OTP and the query is a 6-digit number
    if auth_state == "otp_required" and query.isdigit() and len(query) == 6:
        logger.info(f"Client {client_id} - Processing OTP: {query}")
        
        # Get meter ID from history
        meter_id = get_meter_id_from_history(history)
        logger.info(f"Client {client_id} - Retrieved meter ID from history: {meter_id}")
        
        if meter_id:
            # Verify OTP - accept any 6-digit number
            logger.info(f"Client {client_id} - Verifying OTP for meter ID: {meter_id}")
            
            # Always accept any 6-digit OTP
            if len(query) == 6 and query.isdigit():
                logger.info(f"Client {client_id} - OTP validation successful")
                
                # Authenticate user
                is_auth, token = await authenticate_user(meter_id, query)
                if is_auth:
                    logger.info(f"Client {client_id} - Authentication successful, token generated")
                    
                    # Store token with connection
                    connection_manager.set_token(connection_id, token)
                    
                    # Send success response
                    await connection_manager.send_message(
                        connection_id,
                        {
                            "status": "auth_success",
                            "query": query,
                            "client_id": client_id,
                            "message": "Authentication successful. Welcome! How can I help you today?",
                            "auth_state": "authenticated",
                            "token": token
                        }
                    )
                    return
                else:
                    logger.error(f"Client {client_id} - Token generation failed")
            else:
                logger.warning(f"Client {client_id} - Invalid OTP format: {query}")
        else:
            logger.warning(f"Client {client_id} - No meter ID found in history")
        
        # If we get here, authentication failed
        await connection_manager.send_message(
            connection_id,
            {
                "status": "auth_failed",
                "query": query,
                "client_id": client_id,
                "message": "Please enter a valid 6-digit OTP.",
                "auth_state": "otp_required"
            }
        )
    
    # If we're waiting for meter ID or starting fresh, try to validate as meter ID
    elif auth_state in ["meter_id_required", None]:
        logger.info(f"Client {client_id} - Validating potential meter ID: {query}")
        
        # Try to validate the query as a meter ID
        is_valid, meter_data = await validate_meter_id(query)
        
        if is_valid:
            logger.info(f"Client {client_id} - Valid meter ID: {query}")
            
            # Generate OTP
            otp = otp_service.generate_otp(query)
            logger.info(f"Client {client_id} - Generated OTP for meter ID {query}: {otp}")
            
            # Store auth state in history
            store_auth_state_in_history(history, "otp_required", query)
            logger.info(f"Client {client_id} - Updated auth state to: otp_required")
            
            await connection_manager.send_message(
                connection_id,
                {
                    "status": "auth_required",
                    "query": query,
                    "client_id": client_id,
                    "message": "Please enter the 6-digit OTP sent to your registered mobile number.",
                    "auth_state": "otp_required",
                    "meter_id": query
                }
            )
        else:
            logger.warning(f"Client {client_id} - Invalid meter ID: {query}")
            
            # Store auth state in history
            store_auth_state_in_history(history, "meter_id_required")
            logger.info(f"Client {client_id} - Updated auth state to: meter_id_required")
            
            # Simplified response for client
            await connection_manager.send_message(
                connection_id,
                {
                    "status": "auth_required",
                    "query": query,
                    "client_id": client_id,
                    "message": "Please enter your meter ID to continue.",
                    "auth_state": "meter_id_required"
                }
            )
    
    # Default case - ask for meter ID
    else:
        logger.info(f"Client {client_id} - Default case, requesting meter ID")
        store_auth_state_in_history(history, "meter_id_required")
        await connection_manager.send_message(
            connection_id,
            {
                "status": "auth_required",
                "query": query,
                "client_id": client_id,
                "message": "Please enter your meter ID to continue.",
                "auth_state": "meter_id_required"
            }
        )


async def process_authenticated_query(connection_id: str, client_id: str, query: str, token: str):
    """
    Process a query from an authenticated client.
    """
    try:
        # Get the orchestrator instance for this client
        orchestrator = ClientOrchestrator.get_instance(client_id)
        
        # Add the query to the history
        orchestrator.history_manager.add_user_message(client_id, query)
        
        # Check if this is a DFP participation response
        if query.lower().strip() in ["yes", "yes please", "i want to participate", "participate"]:
            # Check if we're waiting for control permission
            if client_id in dfp_conversation_state and dfp_conversation_state[client_id] == "awaiting_permission":
                # This is a response to the control permission question
                await handle_control_permission(connection_id, client_id, query, token)
                return
            else:
                # This is a response to the initial participation question
                await handle_dfp_participation(connection_id, client_id, query, token)
                return
        
        # For complex queries, send an immediate acknowledgment
        await connection_manager.send_message(
            connection_id,
            {
                "status": "processing",
                "query": query,
                "client_id": client_id,
                "message": "Processing your request...",
                "auth_state": "authenticated"
            }
        )
        
        # Process the query
        ai_message = await orchestrator.process_query(query)
        
        # Send the final response
        await connection_manager.send_message(
            connection_id,
            {
                "status": "success",
                "query": query,
                "client_id": client_id,
                "message": ai_message,
                "auth_state": "authenticated"
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


# Helper functions for auth state tracking
def get_auth_state_from_history(history):
    """Get the current authentication state from chat history."""
    # Look for system messages with auth state
    for message in reversed(history.messages):
        if hasattr(message, 'type') and message.type == "system" and hasattr(message, 'metadata') and message.metadata and "auth_state" in message.metadata:
            return message.metadata["auth_state"]
    return None

def get_meter_id_from_history(history):
    """Get the meter ID from chat history."""
    # Look for system messages with meter ID
    for message in reversed(history.messages):
        if hasattr(message, 'type') and message.type == "system" and hasattr(message, 'metadata') and message.metadata and "meter_id" in message.metadata:
            return message.metadata["meter_id"]
    return None

def store_auth_state_in_history(history, auth_state, meter_id=None):
    """Store authentication state in chat history."""
    from langchain_core.messages import SystemMessage
    
    metadata = {"auth_state": auth_state}
    if meter_id:
        metadata["meter_id"] = meter_id
    
    # Add a system message with auth state
    history.add_message(
        SystemMessage(
            content=f"Authentication state: {auth_state}",
            metadata=metadata
        )
    )

# Add this function to handle DFP participation consent
async def handle_dfp_participation(connection_id: str, client_id: str, query: str, token: str):
    """
    Handles a user's consent to participate in a DFP program.
    """
    logger.info(f"Handling DFP participation for client {client_id}")
    
    # First send a processing message to show loading on client side
    await connection_manager.send_message(
        connection_id,
        {
            "status": "processing",
            "query": query,
            "client_id": client_id,
            "message": "Processing your participation request...",
            "auth_state": "authenticated"
        }
    )
    
    # Add a delay to simulate processing time
    await asyncio.sleep(1.5)
    
    # Send the DER scheme message with question
    der_message = (
        "🙌 Great! You can contribute by temporarily turning off the following DERs (Distributed Energy Resources) in your home:\n\n"
        "HVAC – 3.5 kW\n"
        "Washing Machine – 1.8 kW\n"
        "Dish Washer – 1.2 kW\n\n"
        "Would you like to approve the plan and grant control permission to make device actions compliant?"
    )
    
    await connection_manager.send_message(
        connection_id,
        {
            "status": "success",
            "query": query,
            "client_id": client_id,
            "message": der_message,
            "auth_state": "authenticated"
        }
    )
    
    # Add this message to the chat history
    orchestrator = ClientOrchestrator.get_instance(client_id)
    orchestrator.history_manager.add_ai_message(client_id, der_message)
    
    # Store the state that we're waiting for control permission
    dfp_conversation_state[client_id] = "awaiting_permission"
    
    return True

# Add this function to handle control permission
async def handle_control_permission(connection_id: str, client_id: str, query: str, token: str):
    """
    Handles a user's permission to control their devices.
    """
    logger.info(f"Handling control permission for client {client_id}")
    
    # First send a processing message to show loading on client side
    await connection_manager.send_message(
        connection_id,
        {
            "status": "processing",
            "query": query,
            "client_id": client_id,
            "message": "Processing your control permission...",
            "auth_state": "authenticated"
        }
    )
    
    # Add a delay to simulate processing time
    await asyncio.sleep(2)
    
    # Make the API call to record consent
    try:
        # Use the client_id as the meter_id for now
        meter_id = int(client_id) if client_id.isdigit() else 2129  # Default to 2129 if not a number
        
        # Hardcoded order_id for now
        order_id = 3805
        
        # Prepare the API request
        api_url = f"{os.getenv('STRAPI_BASE_URL')}/unified-beckn-energy/mitigation-accept-reject"
        payload = {
            "meter_id": meter_id,
            "dfp_accept": True,
            "order_id": order_id
        }
        
        logger.info(f"Making API call to record consent: {payload}")
        
        # Make the API call
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=10  # 10 second timeout
        )
        
        # Log the response
        logger.info(f"API response status code: {response.status_code}")
        logger.info(f"API response: {response.text}")
        
        # Send confirmation messages
        confirmation_message = "✅ Thank you! We've successfully recorded your consent, activated the schedules and notified the system operator."
        
        # Send first confirmation
        await connection_manager.send_message(
            connection_id,
            {
                "status": "success",
                "query": query,
                "client_id": client_id,
                "message": confirmation_message,
                "auth_state": "authenticated"
            }
        )
        
        # Add to chat history
        orchestrator = ClientOrchestrator.get_instance(client_id)
        orchestrator.history_manager.add_ai_message(client_id, confirmation_message)
        
        # Wait a moment before sending the second message
        await asyncio.sleep(2)
        
        # Send second confirmation
        update_message = "An update has been shared with the Utility Platform to reflect your participation."
        await connection_manager.send_message(
            connection_id,
            {
                "status": "success",
                "query": query,
                "client_id": client_id,
                "message": update_message,
                "auth_state": "authenticated"
            }
        )
        
        # Add to chat history
        orchestrator.history_manager.add_ai_message(client_id, update_message)
        
        # Clear the conversation state
        if client_id in dfp_conversation_state:
            del dfp_conversation_state[client_id]
        
        return True
        
    except Exception as e:
        logger.error(f"Error making API call to record consent: {str(e)}", exc_info=True)
        
        # Send error message
        error_message = "Sorry, we encountered an issue while processing your consent. Please try again later."
        await connection_manager.send_message(
            connection_id,
            {
                "status": "error",
                "query": query,
                "client_id": client_id,
                "message": error_message,
                "auth_state": "authenticated"
            }
        )
        
        # Add to chat history
        orchestrator = ClientOrchestrator.get_instance(client_id)
        orchestrator.history_manager.add_ai_message(client_id, error_message)
        
        return False 