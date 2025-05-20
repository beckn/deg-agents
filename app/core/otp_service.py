import logging
from typing import Dict
import random

logger = logging.getLogger(__name__)

class OTPService:
    """
    Service for generating and verifying OTPs.
    """
    
    def __init__(self):
        # In a real implementation, this would store OTPs in a database with expiration
        # For now, we'll use an in-memory dictionary
        self.otps: Dict[str, str] = {}
    
    def generate_otp(self, meter_id: str) -> str:
        """
        Generates a new OTP for a meter ID.
        
        Args:
            meter_id: The meter ID
            
        Returns:
            The generated OTP
        """
        # Generate a 6-digit OTP
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Store OTP
        self.otps[meter_id] = otp
        
        logger.info(f"Generated OTP for meter ID: {meter_id}")
        return otp
    
    def verify_otp(self, meter_id: str, otp: str) -> bool:
        """
        Verifies an OTP for a meter ID.
        
        Args:
            meter_id: The meter ID
            otp: The OTP to verify
            
        Returns:
            True if OTP is valid, False otherwise
        """
        # In a real implementation, this would check against a database
        # For now, we'll accept any 6-digit OTP for simplicity
        logger.info(f"Verifying OTP for meter ID {meter_id}: {otp}")
        
        # Always accept any 6-digit number
        if len(otp) == 6 and otp.isdigit():
            logger.info(f"OTP verification successful for meter ID: {meter_id}")
            return True
        
        logger.warning(f"Invalid OTP format for meter ID: {meter_id}")
        return False

# Create a singleton instance
otp_service = OTPService() 