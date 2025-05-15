import json
import time
import uuid
from typing import Any, Dict, List, Type

import requests  # Ensure 'requests' library is installed
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

# Assuming constants.py is in the same directory (package)
from . import constants


class CustomerDetails(BaseModel):
    name: str = Field(description="Customer's full name")
    phone: str = Field(description="Customer's phone number")
    email: str = Field(description="Customer's email address")


class FulfillmentDetails(BaseModel):
    id: str = Field(
        description="Fulfillment ID, typically from a previous step like 'init' or 'select' response"
    )
    customer: CustomerDetails = Field(
        description="Customer details for this fulfillment"
    )


class SolarRetailConfirmInput(BaseModel):
    """Input for SolarRetailConfirmTool."""

    provider_id: str = Field(description="ID of the provider for the item to confirm")
    item_id: str = Field(description="ID of the item to be confirmed")
    transaction_id: str = Field(
        description="Transaction ID from a previous interaction (e.g., init)."
    )
    fulfillments: List[FulfillmentDetails] = Field(
        description="List of fulfillment details, including customer information and fulfillment ID."
    )


class SolarRetailConfirmTool(BaseTool):
    name: str = "solar_retail_item_confirm"
    description: str = (
        "Confirms a solar retail item order with provider, item, transaction, and fulfillment details. "
        "Requires provider_id, item_id, transaction_id, and fulfillment information (including customer details)."
        "Returns the raw JSON response as a string."
    )
    args_schema: Type[BaseModel] = SolarRetailConfirmInput

    def _run(
        self,
        provider_id: str,
        item_id: str,
        transaction_id: str,
        fulfillments: List[Dict[str, Any]],  # Pydantic model will ensure structure
        **kwargs: Any,
    ) -> str:
        """Executes the confirm tool."""
        message_id = str(uuid.uuid4())
        current_timestamp = str(int(time.time()))

        payload = {
            "context": {
                "domain": constants.CONTEXT_DOMAIN,
                "action": constants.CONTEXT_ACTION_CONFIRM,  # Use confirm action
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
                "order": {
                    "provider": {"id": provider_id},
                    "items": [{"id": item_id}],
                    "fulfillments": [
                        {
                            "id": ful[
                                "id"
                            ],  # Accessing dict keys after Pydantic validation
                            "customer": {
                                "person": {"name": ful["customer"]["name"]},
                                "contact": {
                                    "phone": ful["customer"]["phone"],
                                    "email": ful["customer"]["email"],
                                },
                            },
                        }
                        for ful in fulfillments
                    ],
                }
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                constants.CONFIRM_BASE_URL,  # Use confirm base URL
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            return f"Error calling Beckn confirm API: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    async def _arun(
        self,
        provider_id: str,
        item_id: str,
        transaction_id: str,
        fulfillments: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> str:
        """Asynchronously executes the confirm tool."""
        return self._run(
            provider_id=provider_id,
            item_id=item_id,
            transaction_id=transaction_id,
            fulfillments=fulfillments,
            **kwargs,
        )
