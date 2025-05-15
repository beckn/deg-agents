import json
import time
import uuid
from typing import Any, Type

import requests  # Ensure 'requests' library is installed
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# Assuming constants.py is in the same directory (package)
from . import constants


class SolarRetailSearchInput(BaseModel):
    """Input for SolarRetailSearchTool. Currently empty as all parameters are from constants."""

    pass


class SolarRetailSearchTool(BaseTool):
    name: str = "solar_retail_item_search"
    description: str = (
        "Searches for solar retail items using predefined parameters (item: solar, "
        "location: USA/NANP:628) via a Beckn endpoint. Returns the raw JSON response as a string."
    )
    args_schema: Type[BaseModel] = SolarRetailSearchInput

    def _run(self, **kwargs: Any) -> str:
        """Executes the search tool."""
        transaction_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        current_timestamp = str(int(time.time()))

        payload = {
            "context": {
                "domain": constants.CONTEXT_DOMAIN,
                "action": constants.CONTEXT_ACTION,
                "location": {
                    "country": {"code": constants.CONTEXT_LOCATION_COUNTRY_CODE},
                    "city": {"code": constants.CONTEXT_LOCATION_CITY_CODE},
                },
                "version": constants.CONTEXT_VERSION,
                "bap_id": constants.CONTEXT_BAP_ID,
                "bap_uri": constants.CONTEXT_BAP_URI,
                "bpp_id": constants.CONTEXT_BPP_ID,
                "bpp_uri": constants.CONTEXT_BPP_URI,
                "transaction_id": transaction_id,
                "message_id": message_id,
                "timestamp": current_timestamp,
            },
            "message": {
                "intent": {
                    "item": {
                        "descriptor": {
                            "name": constants.MESSAGE_INTENT_ITEM_DESCRIPTOR_NAME
                        }
                    }
                }
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                constants.BASE_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            return response.text  # Return the raw response text (JSON string)
        except requests.exceptions.RequestException as e:
            return f"Error calling Beckn search API: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    async def _arun(self, **kwargs: Any) -> str:
        """Asynchronously executes the search tool.
        Note: This requires an async HTTP client like httpx.
        For simplicity, this example uses a blocking call within the async method.
        In a production scenario, use httpx.AsyncClient.
        """
        # This is a simplified async version. For true async, use an async library.
        # For now, it will call the synchronous version.
        # To implement fully async:
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(...)
        #     return response.text
        return self._run(**kwargs)
