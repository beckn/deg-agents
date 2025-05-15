import json
import time
import uuid
from typing import Any, Dict, List, Type, ClassVar

import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from . import constants


class BecknConfirmInput(BaseModel):
    """Input for BecknConfirmTool."""

    provider_id: str = Field(description="ID of the provider for the item to confirm")
    item_id: str = Field(description="ID of the item to be confirmed")
    fulfillment_id: str = Field(description="Fulfillment ID for the order")

    domain_choices: ClassVar[str] = ", ".join(
        f"{key}: {value[0]}"
        for key, value in constants.CONTEXT_DOMAINS_TO_DESCRIPTOR_MAPPING.items()
    )

    domain: str = Field(
        description=(
            "The domain to search for. Can be one of the following: "
            f"{domain_choices}"
        )
    )


class BecknConfirmTool(BaseTool):
    name: str = "beckn_confirm"
    description: str = (
        "Confirms a solar retail item order with provider, item, transaction, and fulfillment details. "
        "Requires provider_id, item_id, transaction_id, and fulfillment_id. "
        "Returns the raw JSON response as a string."
    )
    args_schema: Type[BaseModel] = BecknConfirmInput

    def _run(
        self,
        fulfillment_id: str,
        domain: str,
        **kwargs: Any,
    ) -> str:
        """Executes the confirm tool."""
        message_id = str(uuid.uuid4())
        current_timestamp = str(int(time.time()))
        transaction_id = str(uuid.uuid4())
        payload = {
            "context": {
                "domain": domain,
                "action": constants.CONTEXT_ACTIONS[2],  # confirm
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
                    "provider": {"id": kwargs["provider_id"]},
                    "items": [{"id": kwargs["item_id"]}],
                    "fulfillments": [
                        {
                            "id": fulfillment_id,
                            "customer": {
                                "person": {"name": "Lisa"},
                                "contact": {
                                    "phone": "876756454",
                                    "email": "LisaS@mailinator.com",
                                },
                            },
                        }
                    ],
                }
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(
                f"{constants.BASE_URL}{constants.CONTEXT_ACTIONS[2]}",
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

    async def _arun(self, **kwargs: Any) -> str:
        """Asynchronously executes the confirm tool."""
        return self._run(**kwargs)
