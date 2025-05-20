from typing import Dict, Any, Optional, Tuple
import logging
import httpx
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Get API URL from environment variables
METER_API_BASE_URL = os.getenv("METER_API_BASE_URL", "https://playground.becknprotocol.io/meter-data-simulator/meters")

async def validate_meter_id(meter_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validates a meter ID by making an API call to the meter data service.
    
    Args:
        meter_id: The meter ID to validate
        
    Returns:
        Tuple of (is_valid, meter_data)
    """
    # Check basic format first
    if not meter_id or not isinstance(meter_id, str):
        logger.warning(f"Invalid meter ID format: {meter_id}")
        return False, None
    
    try:
        # Make API call to validate meter ID
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{METER_API_BASE_URL}/{meter_id}")
            
            # Check if request was successful
            if response.status_code == 200:
                meter_data = response.json()
                logger.info(f"Validated meter ID: {meter_id}")
                return True, meter_data
            elif response.status_code == 404:
                logger.warning(f"Meter ID not found: {meter_id}")
                return False, None
            else:
                logger.error(f"Error validating meter ID {meter_id}: {response.status_code} - {response.text}")
                return False, None
                
    except Exception as e:
        logger.error(f"Exception during meter ID validation: {e}")
        return False, None 