import json
from typing import Any, Type

import requests
from langchain.tools import BaseTool
from pydantic import BaseModel

from . import constants


class OnStatusToolInput(BaseModel):
    """No input is required for OnStatusTool as the payload is predefined."""


class OnStatusTool(BaseTool):
    name: str = "on_status_beckn"
    description: str = (
        "Calls the on_status endpoint of the Beckn BPP client "
        "with a predefined payload. "
        "Returns the raw JSON response as a string."
    )
    args_schema: Type[BaseModel] = OnStatusToolInput

    def _run(self, **kwargs: Any) -> str:
        """Executes the OnStatusTool."""
        headers = {"Content-Type": "application/json"}
        url = "https://bpp-ps-client-deg.becknprotocol.io/on_status"
        payload = {
            "context": {
                "domain": "deg:schemes",
                "location": {
                    "country": {"name": "India", "code": "IND"},
                    "city": {"name": "Bangalore", "code": "std:080"},
                },
                "transaction_id": "a93a5c6f-a420-4e13-b42b-109dd294e16f",
                "message_id": "46ab1501-bba9-4092-bf62-aecbb658ebf1",
                "action": "on_status",
                "timestamp": "2025-05-15T16:23:57.494Z",
                "version": "1.1.0",
                "bap_uri": "https://bap2-ps-network-deg.becknprotocol.io",
                "bap_id": "bap2-ps-network-deg.becknprotocol.io",
                "bpp_id": "bpp-ps-network-deg.becknprotocol.io",
                "bpp_uri": "http://bpp-ps-network-deg.becknprotocol.io",
            },
            "message": {
                "order": {
                    "id": "3789",
                    "created_at": "2025-05-15T16:17:19.113Z",
                    "provider": {
                        "id": "323",
                        "descriptor": {
                            "name": "Pacific Gas and Electric Company (PG&E)",
                            "short_desc": "Demand response and smart energy programs",
                            "long_desc": "PG&E is one of the largest combined natural gas and electric utilities in the United States, offering demand response, time-of-use pricing, and smart thermostat programs to help manage grid load and reduce emissions.",
                            "additional_desc": {"url": "beckn://pge.com"},
                            "images": [
                                {
                                    "url": "https://www.pge.com/library/images/logos/pge-logo-blue.svg",
                                    "size_type": "sm",
                                }
                            ],
                        },
                        "short_desc": "Demand response and smart energy programs",
                        "locations": [
                            {
                                "id": "28",
                                "gps": "37.7910,-122.3969",
                                "address": "245 Market Street, San Francisco",
                                "city": {"name": "San Francisco"},
                                "country": {"name": "United States"},
                                "state": {"name": "CA"},
                                "area_code": "94105",
                            }
                        ],
                        "rateable": True,
                    },
                    "items": [
                        {
                            "id": "458",
                            "descriptor": {
                                "name": "Home Battery Discharge Program",
                                "code": "Home Battery Discharge Program",
                                "short_desc": "Discharge home battery during peak demand hours",
                                "long_desc": "A program that enables residential users with battery storage to discharge energy back to the grid during peak demand events. Participants receive compensation for every kWh discharged.",
                                "images": [
                                    {
                                        "url": "https://static.vecteezy.com/system/resources/previews/004/820/773/non_2x/upside-down-arrow-with-electrical-plug-and-lightning-free-vector.jpg",
                                        "size_type": "sm",
                                    }
                                ],
                            },
                            "rating": "null",
                            "rateable": True,
                            "location_ids": ["28"],
                            "price": {"value": "0", "currency": "USD"},
                            "quantity": {
                                "available": {
                                    "count": 500,
                                    "measure": {"value": "500"},
                                },
                                "selected": {"count": 1},
                            },
                            "category_ids": ["41"],
                            "fulfillment_ids": ["615"],
                        }
                    ],
                    "price": {"value": "0", "currency": "USD"},
                    "fulfillments": [
                        {
                            "id": "616",
                            "state": {
                                "descriptor": {
                                    "code": "ORDER_RECEIVED",
                                    "short_desc": "ORDER RECEIVED",
                                },
                                "updated_at": "2025-05-15T16:23:57.444Z",
                            },
                            "customer": {
                                "contact": {
                                    "email": "LisaS@mailinator.com",
                                    "phone": "876756454",
                                },
                                "person": {"name": "Lisa"},
                            },
                            "stops": [{"type": "start"}],
                            "agent": {"person": {"name": " "}},
                            "rating": "null",
                            "rateable": True,
                        }
                    ],
                    "quote": {
                        "price": {"value": "100", "currency": "USD"},
                        "breakup": [
                            {
                                "title": "BASE PRICE",
                                "price": {"currency": "USD", "value": "0"},
                                "item": {"id": "458"},
                            },
                            {
                                "title": "TAX",
                                "price": {"currency": "USD", "value": "0"},
                                "item": {"id": "458"},
                            },
                        ],
                    },
                    "status": "ACTIVE",
                }
            },
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            return f"Error calling OnStatus API: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    async def _arun(self, **kwargs: Any) -> str:
        """Asynchronously executes the OnStatusTool."""
        return self._run(**kwargs)
