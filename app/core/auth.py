from typing import Dict, Any, Optional, Tuple
import logging
from app.core.session_manager import session_manager
from app.core.meter_validator import validate_meter_id as api_validate_meter_id

logger = logging.getLogger(__name__)

async def validate_meter_id(meter_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validates a meter ID and returns associated data if valid.
    
    Args:
        meter_id: The meter ID to validate
        
    Returns:
        Tuple of (is_valid, meter_data)
    """
    # Use the API validation from meter_validator.py
    return await api_validate_meter_id(meter_id)

async def verify_otp(meter_id: str, otp: str) -> bool:
    """
    Verifies an OTP for a meter ID.
    
    Args:
        meter_id: The meter ID
        otp: The OTP to verify
        
    Returns:
        True if OTP is valid, False otherwise
    """
    # In a real implementation, this would verify the OTP against a database or service
    # For now, we'll accept any 6-digit OTP
    
    if len(otp) == 6 and otp.isdigit():
        logger.info(f"Verified OTP for meter ID: {meter_id}")
        return True
    
    logger.warning(f"Invalid OTP format for meter ID: {meter_id}")
    return False

async def authenticate_user(meter_id: str, otp: str) -> Tuple[bool, Optional[str]]:
    """
    Authenticates a user with meter ID and OTP.
    
    Args:
        meter_id: The meter ID
        otp: The OTP
        
    Returns:
        Tuple of (is_authenticated, token)
    """
    logger.info(f"Authenticating user with meter ID: {meter_id}")
    
    # Validate meter ID
    is_valid, meter_data = await validate_meter_id(meter_id)
    if not is_valid:
        logger.warning(f"Invalid meter ID during authentication: {meter_id}")
        return False, None
    
    # Verify OTP - accept any 6-digit number
    if not (len(otp) == 6 and otp.isdigit()):
        logger.warning(f"Invalid OTP format during authentication: {otp}")
        return False, None
    
    logger.info(f"Authentication successful for meter ID: {meter_id}")
    
    # Create session and get token
    token = session_manager.create_session(meter_id, meter_data)
    
    return True, token

def is_authenticated(token: str) -> bool:
    """
    Checks if a token is authenticated.
    
    Args:
        token: The session token
        
    Returns:
        True if authenticated, False otherwise
    """
    logger.info(f"Checking authentication for token: {token}")
    result = session_manager.validate_token(token)
    logger.info(f"Token validation result: {result}")
    return result

def get_user_data(token: str) -> Optional[Dict[str, Any]]:
    """
    Gets user data for an authenticated token.
    
    Args:
        token: The session token
        
    Returns:
        User data or None if not authenticated
    """
    return session_manager.get_session_data(token) 