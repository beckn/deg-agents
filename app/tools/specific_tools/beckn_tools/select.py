import json
import time
import uuid
from typing import Any, Type

import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from . import constants


class BecknSelectSelectInput(BaseModel):
    """Input for BecknSelectTool."""

    domain: str = Field(
        description=(
            "The domain to search for. Can be one of the following: "
            f"{constants.CONTEXT_DOMAINS_TO_DESCRIPTOR_MAPPING.keys()}"
        )
    )
    item_id: str = Field(
        description="The ID of the item to select. This is the 'item_id' from the search tool response."
    )
    provider_id: str = Field(
        description="The ID of the provider to select. This is the 'provider_id' from the search tool response."
    )


class BecknSelectTool(BaseTool):
    name: str = "beckn_select"
    description: str = (
        "Searches for an item in a given domain using predefined parameters"
        "location: USA/NANP:628) via a Beckn endpoint. Returns the raw JSON response as a string."
    )
    args_schema: Type[BaseModel] = BecknSelectSelectInput

    def _run(self, **kwargs: Any) -> str:
        """Executes the select tool."""
        transaction_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        current_timestamp = str(int(time.time()))
        domain = kwargs["domain"]

        payload = {
            "context": {
                "domain": domain,
                "action": constants.CONTEXT_ACTIONS[1],  # select
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
                    "provider": {
                        "id": kwargs["provider_id"],
                    },
                    "items": [
                        {
                            "id": kwargs["item_id"],
                        }
                    ],
                },
            },
        }
        print(payload)

        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                f"{constants.BASE_URL}{constants.CONTEXT_ACTIONS[1]}",
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            return f"Error calling Beckn select API: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    async def _arun(self, **kwargs: Any) -> str:
        """Asynchronously executes the select tool.
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
