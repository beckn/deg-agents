import json
import time
import uuid
from typing import Any, Type

import requests  # Ensure 'requests' library is installed
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# Assuming constants.py is in the same directory (package)
from . import constants


class SolarRetailInitInput(BaseModel):
    """Input for SolarRetailInitTool."""

    provider_id: str = Field(
        description="ID of the provider for the item to initialize"
    )
    item_id: str = Field(description="ID of the item to be initialized")
    transaction_id: str = Field(
        description="Transaction ID from a previous interaction (e.g., select)."
    )


class SolarRetailInitTool(BaseTool):
    name: str = "solar_retail_item_init"
    description: str = (
        "Initializes a solar retail item order with a specific provider using their IDs and a transaction ID. "
        "Requires provider_id, item_id, and transaction_id from a previous interaction (e.g., select)."
        "Returns the raw JSON response as a string."
    )
    args_schema: Type[BaseModel] = SolarRetailInitInput

    def _run(
        self, provider_id: str, item_id: str, transaction_id: str, **kwargs: Any
    ) -> str:
        """Executes the init tool."""
        message_id = str(uuid.uuid4())
        current_timestamp = str(int(time.time()))

        payload = {
            "context": {
                "domain": constants.CONTEXT_DOMAIN,
                "action": constants.CONTEXT_ACTION_INIT,  # Use init action
                "location": {
                    "country": {"code": constants.CONTEXT_LOCATION_COUNTRY_CODE},
                    "city": {"code": constants.CONTEXT_LOCATION_CITY_CODE},
                },
                "version": constants.CONTEXT_VERSION,
                "bap_id": constants.CONTEXT_BAP_ID,
                "bap_uri": constants.CONTEXT_BAP_URI,
                "bpp_id": constants.CONTEXT_BPP_ID,
                "bpp_uri": constants.CONTEXT_BPP_URI,
                "transaction_id": transaction_id,  # Use provided transaction_id
                "message_id": message_id,
                "timestamp": current_timestamp,
            },
            "message": {
                "order": {
                    "provider": {"id": provider_id},
                    "items": [{"id": item_id}],
                }
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                constants.INIT_BASE_URL,  # Use init base URL
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            return response.text  # Return the raw response text (JSON string)
        except requests.exceptions.RequestException as e:
            return f"Error calling Beckn init API: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    async def _arun(
        self, provider_id: str, item_id: str, transaction_id: str, **kwargs: Any
    ) -> str:
        """Asynchronously executes the init tool.
        Note: This requires an async HTTP client like httpx.
        For simplicity, this example uses a blocking call within the async method.
        """
        return self._run(
            provider_id=provider_id,
            item_id=item_id,
            transaction_id=transaction_id,
            **kwargs,
        )
