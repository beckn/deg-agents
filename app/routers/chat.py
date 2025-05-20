from fastapi import APIRouter, HTTPException, Header
from typing import Optional
import logging
from app.models.chat import ChatRequest, ChatResponse, AuthRequest, AuthResponse
from app.core.orchestrator import ClientOrchestrator
from app.core.history_manager import chat_history_manager
from app.core.auth import authenticate_user, is_authenticated, get_user_data
from app.core.meter_validator import validate_meter_id
from app.core.otp_service import otp_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Chat endpoint that accepts query and client_id,
    then processes it through the ClientOrchestrator.
    
    If no authorization token is provided, it will check if the query
    is a meter ID for authentication.
    """
    if not request.query or not request.client_id:
        raise HTTPException(status_code=400, detail="Query and client_id are required.")

    # Log the authorization header
    logger.info(f"Client {request.client_id} - Authorization header: {authorization}")
    
    # Get chat history to track state
    history = chat_history_manager.get_history(request.client_id)
    
    # Check authentication
    if not authorization or not is_authenticated(authorization):
        logger.info(f"Client {request.client_id} - Not authenticated. Token: {authorization}")
        
        # Check if we're in the middle of authentication flow
        auth_state = get_auth_state_from_history(history)
        logger.info(f"Client {request.client_id} - Current auth state: {auth_state}")
        
        # If we're waiting for OTP and the query is a 6-digit number
        if auth_state == "otp_required" and request.query.isdigit() and len(request.query) == 6:
            logger.info(f"Client {request.client_id} - Processing OTP: {request.query}")
            
            # Get meter ID from history
            meter_id = get_meter_id_from_history(history)
            logger.info(f"Client {request.client_id} - Retrieved meter ID from history: {meter_id}")
            
            if meter_id:
                # Verify OTP - accept any 6-digit number
                logger.info(f"Client {request.client_id} - Verifying OTP for meter ID: {meter_id}")
                
                # Always accept any 6-digit OTP
                if len(request.query) == 6 and request.query.isdigit():
                    logger.info(f"Client {request.client_id} - OTP validation successful")
                    
                    # Authenticate user
                    is_auth, token = await authenticate_user(meter_id, request.query)
                    if is_auth:
                        logger.info(f"Client {request.client_id} - Authentication successful, token generated")
                        return ChatResponse(
                            status="auth_success",
                            query=request.query,
                            client_id=request.client_id,
                            message=f"Authentication successful. Welcome! How can I help you today?",
                            auth_state="authenticated",
                            token=token
                        )
                    else:
                        logger.error(f"Client {request.client_id} - Token generation failed")
                else:
                    logger.warning(f"Client {request.client_id} - Invalid OTP format: {request.query}")
            else:
                logger.warning(f"Client {request.client_id} - No meter ID found in history")
            
            return ChatResponse(
                status="auth_failed",
                query=request.query,
                client_id=request.client_id,
                message="Please enter a valid 6-digit OTP.",
                auth_state="otp_required"
            )
        
        # If we're waiting for meter ID or starting fresh, try to validate as meter ID
        elif auth_state in ["meter_id_required", None]:
            logger.info(f"Client {request.client_id} - Validating potential meter ID: {request.query}")
            
            # Try to validate the query as a meter ID
            is_valid, meter_data = await validate_meter_id(request.query)
            
            if is_valid:
                logger.info(f"Client {request.client_id} - Valid meter ID: {request.query}")
                
                # Generate OTP
                otp = otp_service.generate_otp(request.query)
                logger.info(f"Client {request.client_id} - Generated OTP for meter ID {request.query}: {otp}")
                
                # Store auth state in history
                store_auth_state_in_history(history, "otp_required", request.query)
                logger.info(f"Client {request.client_id} - Updated auth state to: otp_required")
                
                return ChatResponse(
                    status="auth_required",
                    query=request.query,
                    client_id=request.client_id,
                    message=f"Please enter the 6-digit OTP sent to your registered mobile number.",
                    auth_state="otp_required",
                    meter_id=request.query
                )
            else:
                logger.warning(f"Client {request.client_id} - Invalid meter ID: {request.query}")
                
                # Store auth state in history
                store_auth_state_in_history(history, "meter_id_required")
                logger.info(f"Client {request.client_id} - Updated auth state to: meter_id_required")
                
                # Simplified response for client
                return ChatResponse(
                    status="auth_required",
                    query=request.query,
                    client_id=request.client_id,
                    message="Please enter your meter ID to continue.",
                    auth_state="meter_id_required"
                )
        
        # Default case - ask for meter ID
        logger.info(f"Client {request.client_id} - Default case, requesting meter ID")
        store_auth_state_in_history(history, "meter_id_required")
        return ChatResponse(
            status="auth_required",
            query=request.query,
            client_id=request.client_id,
            message="Please enter your meter ID to continue.",
            auth_state="meter_id_required"
        )

    # User is authenticated, process the query normally
    logger.info(f"Client {request.client_id} - User is authenticated, processing query")
    try:
        # Get user data from token
        user_data = get_user_data(authorization)
        if not user_data:
            logger.warning(f"Client {request.client_id} - Session expired")
            store_auth_state_in_history(history, "meter_id_required")
            return ChatResponse(
                status="auth_required",
                query=request.query,
                client_id=request.client_id,
                message="Your session has expired. Please enter your meter ID to continue.",
                auth_state="meter_id_required"
            )
        
        # Get or create the orchestrator instance for this client
        orchestrator = ClientOrchestrator.get_instance(request.client_id)

        # Process the query
        ai_message = await orchestrator.process_query(request.query)

        return ChatResponse(
            status="success",
            query=request.query,
            client_id=request.client_id,
            message=ai_message,
            auth_state="authenticated"
        )
    except Exception as e:
        # Handle exceptions
        logger.error(f"An unexpected error occurred for client {request.client_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"An internal server error occurred: {e}"
        )


@router.post("/auth", response_model=AuthResponse)
async def authenticate(request: AuthRequest):
    """
    Authenticates a user with meter ID and OTP.
    """
    if not request.meter_id:
        raise HTTPException(status_code=400, detail="Meter ID is required.")
    
    # If OTP is provided, verify it
    if request.otp:
        is_auth, token = await authenticate_user(request.meter_id, request.otp)
        if is_auth:
            return AuthResponse(
                status="success",
                message="Authentication successful.",
                token=token
            )
        else:
            return AuthResponse(
                status="error",
                message="Invalid OTP. Please try again."
            )
    
    # If only meter ID is provided, validate it and request OTP
    is_valid, _ = await validate_meter_id(request.meter_id)
    if is_valid:
        # Generate OTP (in a real system, this would be sent to the user)
        otp = otp_service.generate_otp(request.meter_id)
        
        return AuthResponse(
            status="otp_required",
            message="Please enter the 6-digit OTP sent to your registered mobile number."
        )
    else:
        return AuthResponse(
            status="error",
            message="Invalid meter ID. Please enter a valid meter ID."
        )


# Optional: Endpoint to clear a specific client's state (for debugging/testing)
@router.delete("/{client_id}/clear_state", status_code=204)
async def clear_client_state(client_id: str):
    """
    Clears the cached orchestrator instance and chat history for a specific client.
    Useful for testing or resetting a client's session.
    """
    ClientOrchestrator.clear_client_instance(client_id)
    # Also clear history from the global manager

    chat_history_manager.clear_history(client_id)
    print(f"State and history cleared for client_id: {client_id}")
    return None


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
