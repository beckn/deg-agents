from typing import Dict, Any, Optional
import time
import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages user sessions based on meter IDs.
    Handles token generation, validation, and session data storage.
    """
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.token_to_meter_id: Dict[str, str] = {}
        self.session_timeout = 3600  # 1 hour in seconds
    
    def create_session(self, meter_id: str, meter_data: Dict[str, Any]) -> str:
        """
        Creates a new session for a meter ID and returns a token.
        
        Args:
            meter_id: The meter ID for the user
            meter_data: Data associated with the meter
            
        Returns:
            A session token
        """
        # Generate a unique token
        token = f"{meter_id}_{uuid.uuid4().hex[:10]}"
        
        # Create session data
        session_data = {
            "meter_id": meter_id,
            "meter_data": meter_data,
            "created_at": datetime.now(),
            "last_active": datetime.now(),
            "authenticated": True
        }
        
        # Store session
        self.sessions[meter_id] = session_data
        self.token_to_meter_id[token] = meter_id
        
        logger.info(f"Created session for meter ID: {meter_id}")
        return token
    
    def validate_token(self, token: str) -> bool:
        """
        Validates a session token.
        
        Args:
            token: The session token
            
        Returns:
            True if valid, False otherwise
        """
        logger.info(f"Validating token: {token}")
        logger.info(f"Current tokens: {list(self.token_to_meter_id.keys())}")
        
        if not token or token not in self.token_to_meter_id:
            logger.warning(f"Invalid token: {token}")
            return False
        
        meter_id = self.token_to_meter_id[token]
        
        if meter_id not in self.sessions:
            logger.warning(f"No session for meter ID: {meter_id}")
            return False
        
        # Update last active time
        self.sessions[meter_id]["last_active"] = datetime.now()
        
        logger.info(f"Token validated successfully for meter ID: {meter_id}")
        return True
    
    def get_session_data(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Gets session data for a token.
        
        Args:
            token: The session token
            
        Returns:
            Session data or None if token is invalid
        """
        if not self.validate_token(token):
            return None
        
        meter_id = self.token_to_meter_id[token]
        return self.sessions[meter_id]
    
    def update_session_data(self, token: str, data_updates: Dict[str, Any]) -> bool:
        """
        Updates session data for a token.
        
        Args:
            token: The session token
            data_updates: Data to update in the session
            
        Returns:
            True if update was successful, False otherwise
        """
        if not self.validate_token(token):
            return False
        
        meter_id = self.token_to_meter_id[token]
        session = self.sessions[meter_id]
        
        # Update session data
        for key, value in data_updates.items():
            if key != "meter_id" and key != "created_at":  # Protect critical fields
                session[key] = value
        
        return True
    
    def end_session(self, token: str) -> bool:
        """
        Ends a session for a token.
        
        Args:
            token: The session token
            
        Returns:
            True if session was ended, False if token was invalid
        """
        if token not in self.token_to_meter_id:
            return False
        
        meter_id = self.token_to_meter_id[token]
        
        # Clean up
        if meter_id in self.sessions:
            del self.sessions[meter_id]
        
        del self.token_to_meter_id[token]
        
        logger.info(f"Ended session for meter ID: {meter_id}")
        return True
    
    def get_meter_id_from_token(self, token: str) -> Optional[str]:
        """
        Gets the meter ID associated with a token.
        
        Args:
            token: The session token
            
        Returns:
            Meter ID or None if token is invalid
        """
        if not self.validate_token(token):
            return None
        
        return self.token_to_meter_id[token]
    
    def cleanup_expired_sessions(self):
        """
        Cleans up expired sessions.
        """
        current_time = datetime.now()
        tokens_to_remove = []
        
        for token, meter_id in self.token_to_meter_id.items():
            if meter_id in self.sessions:
                session = self.sessions[meter_id]
                last_active = session["last_active"]
                
                if (current_time - last_active).total_seconds() > self.session_timeout:
                    tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            self.end_session(token)
        
        logger.info(f"Cleaned up {len(tokens_to_remove)} expired sessions")

# Create a singleton instance
session_manager = SessionManager() 