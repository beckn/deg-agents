import json
import time
import uuid
import logging
from typing import Any, Type, Dict, Optional, List, ClassVar, Tuple

import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from cachetools import TTLCache

# Get the logger
logger = logging.getLogger(__name__)

# Create a cache with a TTL of 1 hour and a maximum size of 100 items
# The key is a string (e.g., "dfp_options") and the value is any Python object
cache = TTLCache(maxsize=100, ttl=3600)

# Initialize the cache with default DFP options
cache["dfp_options"] = [
    {
        "id": "DDR",
        "name": "Dynamic Demand Response",
        "description": "Dynamic Demand Response (DDR) rewards participants who can rapidly shift or curtail electricity usage during frequent, short-notice events.",
        "reward": "$3–4.5 per kWh shifted",
        "bonus": "15% extra if >90% compliance monthly",
        "penalty": "15% reduction in incentives if compliance <75%",
        "category": "Residential",
        "minimum_load": "5 kW"
    },
    {
        "id": "EDR",
        "name": "Emergency Demand Reduction",
        "description": "Emergency Demand Reduction (EDR) is designed for consumers who can rapidly curtail significant energy use during critical, rare grid emergencies.",
        "reward": "$250/year per kW available",
        "bonus": "$10.00 per kWh curtailed during events",
        "penalty": "50% annual availability fee reduction per missed event",
        "category": "Residential",
        "minimum_load": "5 kW"
    }
]

# Log the initial state of the cache
logger.info("Initializing DFP options cache with default values")
logger.info(f"Initial cache contains {len(cache['dfp_options'])} options")
for i, option in enumerate(cache["dfp_options"]):
    logger.info(f"Initial Option {i+1}: {option.get('name', 'Unknown')} ({option.get('id', 'Unknown')})")

# Constants for the DFP search API
BASE_URL = "https://bap-ps-client-deg.becknprotocol.io/search"
CONTEXT_DOMAIN = "deg:schemes"
CONTEXT_ACTION = "search"
CONTEXT_LOCATION_COUNTRY_CODE = "USA"
CONTEXT_LOCATION_CITY_CODE = "NANP:628"
CONTEXT_VERSION = "1.1.0"
CONTEXT_BAP_ID = "bap-ps-network-deg.becknprotocol.io"
CONTEXT_BAP_URI = "https://bap-ps-network-deg.becknprotocol.io"
CONTEXT_BPP_ID = "bpp-ps-network-deg.becknprotocol.io"
CONTEXT_BPP_URI = "https://bpp-ps-network-deg.becknprotocol.io"


class DFPSearchInput(BaseModel):
    query: str = Field(description="The query to search for DFP options")


class DFPSearchTool(BaseTool):
    name: str = "dfp_search"
    description: str = "Search for Demand Flexibility Program (DFP) options"
    args_schema: Type[BaseModel] = DFPSearchInput
    
    def _run(self, query: str) -> str:
        """
        Search for DFP options.
        
        Args:
            query: The query to search for DFP options
            
        Returns:
            The DFP options as a formatted string
        """
        logger.info(f"DFPSearchTool running with query: {query}")
        # logger.info(f"Before API call, cache contains {len(cache['dfp_options'])} options")
        
        try:
            # Try to call the actual API
            logger.info("Attempting to call DFP API...")
            response, raw_data = self._call_dfp_api(query)
            if response:
                # Store the options in the cache
                api_options = raw_data.get("options", [])
                logger.info(f"API options: {api_options}")
                if api_options:
                    cache["dfp_options"] = api_options
                    logger.info(f"API call successful, updated cache with {len(cache['dfp_options'])} options from API")
                    for i, option in enumerate(cache["dfp_options"]):
                        logger.info(f"Updated Option {i+1}: {option.get('name', 'Unknown')} ({option.get('id', 'Unknown')})")
                else:
                    logger.warning("API returned no options, keeping existing cache")
                return response
        except Exception as e:
            logger.error(f"Error calling DFP API: {str(e)}", exc_info=True)
            logger.info("Keeping existing cache due to API error")
            # Fall back to hardcoded response
        
        # Return hardcoded response as fallback
        logger.info("Using hardcoded fallback response")
        logger.info(f"After API call (or error), cache contains {len(cache['dfp_options'])} options")
        for i, option in enumerate(cache["dfp_options"]):
            logger.info(f"Current Option {i+1}: {option.get('name', 'Unknown')} ({option.get('id', 'Unknown')})")
        
        # Return the formatted fallback response
        fallback_response = """
Here are the available Demand Flexibility Program (DFP) options:

Option 1: Dynamic Demand Response (DDR)
Dynamic Demand Response (DDR) rewards participants who can rapidly shift or curtail electricity usage during frequent, short-notice events. Participants receive moderately high per-event compensation due to their ability to reliably and promptly adjust energy consumption patterns, significantly aiding grid stability and renewable energy integration.
Reward: $3–4.5 per kWh shifted
Bonus: 15% extra if >90% compliance monthly
Penalty: 15% reduction in incentives if compliance <75%
Category: Residential
Minimum Load: 5 kW

Option 2: Emergency Demand Reduction (EDR)
Emergency Demand Reduction (EDR) is designed for consumers who can rapidly curtail significant energy use during critical, rare grid emergencies. These are infrequent but urgent events requiring immediate action. Participants are compensated significantly for availability but face substantial penalties for non-compliance due to critical grid dependence.
Reward: $250/year per kW available
Bonus: $10.00 per kWh curtailed during events
Penalty: 50% annual availability fee reduction per missed event
Category: Residential
Minimum Load: 5 kW
"""
        logger.info(f"Returning fallback response: {fallback_response[:100]}...")
        return fallback_response.strip()
    
    def _call_dfp_api(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call the DFP API to get DFP options.
        
        Args:
            query: The query to search for DFP options
            
        Returns:
            A tuple of (formatted_response, raw_data)
        """
        # Generate a transaction ID
        transaction_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        current_timestamp = str(int(time.time()))
        
        # Prepare the payload
        payload = {
            "context": {
                "domain": CONTEXT_DOMAIN,
                "action": CONTEXT_ACTION,
                "location": {
                    "country": {
                        "code": CONTEXT_LOCATION_COUNTRY_CODE
                    },
                    "city": {
                        "code": CONTEXT_LOCATION_CITY_CODE
                    }
                },
                "version": CONTEXT_VERSION,
                "transaction_id": transaction_id,
                "message_id": message_id,
                "timestamp": current_timestamp,
                "bap_id": CONTEXT_BAP_ID,
                "bap_uri": CONTEXT_BAP_URI,
                "bpp_id": CONTEXT_BPP_ID,
                "bpp_uri": CONTEXT_BPP_URI
            },
            "message": {
                "intent": {
                    "provider": {
                        "descriptor": {
                            "name": "GridSmart Energy Solutions"
                        }
                    }
                }
            }
        }
        
        logger.info(f"Sending API request to {BASE_URL} with payload: {json.dumps(payload)}")
        
        # Make the API call
        response = requests.post(BASE_URL, json=payload)
        
        # Check if the call was successful
        if response.status_code == 200:
            # Parse the response
            response_data = response.json()
            logger.info(f"API response status code: 200")
            logger.info(f"API response: {json.dumps(response_data)}")
            
            # Extract and structure the raw data for later use
            raw_data = self._extract_raw_data(response_data)
            # logger.info(f"Extracted raw data: {json.dumps(raw_data)}")
            
            # Format the response for the agent
            formatted_response = self._format_dfp_api_response(response_data)
            logger.info(f"Formatted response: {formatted_response[:200]}...")
            
            return formatted_response, raw_data
        else:
            logger.error(f"API call failed with status code {response.status_code}: {response.text}")
            raise Exception(f"API call failed with status code {response.status_code}: {response.text}")
    
    def _extract_raw_data(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and structure the raw data from the API response for later use.
        
        Args:
            response_data: The response data from the API
            
        Returns:
            Structured data for later use
        """
        options = []
        
        try:
            # The response has a 'responses' array
            responses = response_data.get("responses", [])
            if not responses:
                logger.warning("No responses found in API response")
                return {"options": []}
            
            # Get the first response
            first_response = responses[0]
            
            # Get the catalog from the message
            catalog = first_response.get("message", {}).get("catalog", {})
            
            # Get the providers
            providers = catalog.get("providers", [])
            
            if not providers:
                logger.warning("No providers found in API response")
                return {"options": []}
            
            for provider in providers:
                # Get the items (DFP options)
                items = provider.get("items", [])
                
                for item in items:
                    item_id = item.get("id", "Unknown")
                    
                    # Get the descriptor
                    descriptor = item.get("descriptor", {})
                    item_name = descriptor.get("name", "Unknown")
                    item_description = descriptor.get("long_desc", "No description available")
                    
                    # Get the price
                    price = item.get("price", {})
                    reward = price.get("value", "Unknown")
                    currency = price.get("currency", "USD")
                    
                    # Get the category
                    category = "Unknown"
                    category_ids = item.get("category_ids", [])
                    if category_ids:
                        # For simplicity, just use the first category ID
                        category = category_ids[0]
                    
                    # Get the tags
                    tags = item.get("tags", [])
                    
                    # Initialize bonus and penalty
                    bonus = "Unknown"
                    penalty = "Unknown"
                    minimum_load = "Unknown"
                    
                    # Extract information from tags
                    for tag in tags:
                        tag_list = tag.get("list", [])
                        
                        for tag_item in tag_list:
                            descriptor = tag_item.get("descriptor", {})
                            name = descriptor.get("name", "")
                            
                            if name == "Reward":
                                reward = tag_item.get("value", reward)
                            elif name == "Bonus":
                                bonus = tag_item.get("value", bonus)
                            elif name == "Penalties":
                                penalty = tag_item.get("value", penalty)
                            elif name == "Minimum sanctioned load":
                                minimum_load = tag_item.get("value", minimum_load)
                            elif name == "Categories":
                                category = tag_item.get("value", category)
                    
                    # Add to options
                    options.append({
                        "id": item_id,
                        "name": item_name,
                        "description": item_description,
                        "reward": reward,
                        "bonus": bonus,
                        "penalty": penalty,
                        "category": category,
                        "minimum_load": minimum_load,
                        "raw_item": item  # Store the raw item for complete data
                    })
                    
                    logger.info(f"Extracted option: {item_name}")
            
            logger.info(f"Extracted {len(options)} options from API response")
        except Exception as e:
            logger.error(f"Error extracting raw data: {str(e)}", exc_info=True)
        
        return {"options": options}
    
    def _format_dfp_api_response(self, response_data: Dict[str, Any]) -> str:
        """
        Format the DFP API response for the agent using Markdown.
        
        Args:
            response_data: The response data from the API
            
        Returns:
            A formatted string with the DFP options in Markdown
        """
        try:
            # The response has a 'responses' array
            responses = response_data.get("responses", [])
            if not responses:
                logger.warning("No responses found in API response")
                return "No DFP options found."
            
            # Get the first response
            first_response = responses[0]
            
            # Get the catalog from the message
            catalog = first_response.get("message", {}).get("catalog", {})
            
            # Get the providers
            providers = catalog.get("providers", [])
            
            if not providers:
                logger.warning("No providers found in API response")
                return "No DFP options found."
            
            # Format the options with Markdown
            formatted_options = "Based on the current stress levels, here are the available **Demand Flexibility Program (DFP)** options:\n\n"
            
            for provider_index, provider in enumerate(providers, 1):
                # Get the items (DFP options)
                items = provider.get("items", [])
                
                if not items:
                    continue
                
                for item_index, item in enumerate(items, 1):
                    # Get the descriptor
                    descriptor = item.get("descriptor", {})
                    item_name = descriptor.get("name", f"Option {provider_index}.{item_index}")
                    item_description = descriptor.get("long_desc", "No description available")
                    
                    # Format the option with Markdown
                    formatted_options += f"### Option {item_index}: {item_name}\n\n"
                    formatted_options += f"{item_description}\n\n"
                    
                    # Get the tags
                    tags = item.get("tags", [])
                    
                    # Extract information from tags and format as bullet points
                    reward = "Unknown"
                    bonus = "Unknown"
                    penalty = "Unknown"
                    category = "Unknown"
                    minimum_load = "Unknown"
                    
                    for tag in tags:
                        tag_list = tag.get("list", [])
                        
                        for tag_item in tag_list:
                            descriptor = tag_item.get("descriptor", {})
                            name = descriptor.get("name", "")
                            value = tag_item.get("value", "Unknown")
                            
                            if name == "Reward":
                                reward = value
                            elif name == "Bonus":
                                bonus = value
                            elif name == "Penalties":
                                penalty = value
                            elif name == "Minimum sanctioned load":
                                minimum_load = value
                            elif name == "Categories":
                                category = value
                    
                    # Add bullet points for all properties
                    formatted_options += f"- **Category**: {category}  \n"
                    formatted_options += f"- **Minimum Load**: {minimum_load}  \n"
                    formatted_options += f"- **Reward**: {reward}  \n"
                    formatted_options += f"- **Bonus**: {bonus}  \n"
                    formatted_options += f"- **Penalty**: {penalty}  \n"
                    
                    # Add spacing between options (instead of horizontal rule)
                    formatted_options += "\n\n"
            
            return formatted_options
        except Exception as e:
            logger.error(f"Error formatting DFP API response: {str(e)}", exc_info=True)
            # Return a generic message if formatting fails
            return "Error formatting DFP options. Please try again."
    
    async def _arun(self, query: str) -> str:
        """
        Async version of _run.
        
        Args:
            query: The query to search for DFP options
            
        Returns:
            The DFP options
        """
        return self._run(query) 