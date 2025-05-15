import requests
from langchain.tools import BaseTool
from typing import Type, Any
from pydantic import BaseModel, Field
import json

from .constants import (
    UPDATE_ER_ENDPOINT_URL,
    UPDATE_ER_REQUEST_HEADERS,
    UPDATE_ER_REQUEST_BODY_TEMPLATE,
)


class UpdateERInput(BaseModel):
    client_id: int = Field(
        description="The client's meter ID to update their energy resource status."
    )


class UpdateERTool(BaseTool):
    name: str = "update_energy_resource_to_prosumer"
    description: str = (
        "Updates an existing energy resource (user) to 'PROSUMER' type. "
        "This is typically used when a consumer installs a solar panel or similar energy generation unit. "
        "Requires the client's meter ID."
    )
    args_schema: Type[BaseModel] = UpdateERInput

    def _run(self, client_id: int, **kwargs: Any) -> str:
        """Updates the energy resource type to PROSUMER for the given client_id."""
        try:
            request_body = UPDATE_ER_REQUEST_BODY_TEMPLATE.copy()
            request_body["data"]["meter"] = client_id

            print(f"UpdateERTool attempting to update client_id: {client_id}")
            print(f"Request URL: {UPDATE_ER_ENDPOINT_URL}")
            print(f"Request Headers: {UPDATE_ER_REQUEST_HEADERS}")
            print(f"Request Body: {json.dumps(request_body)}")

            response = requests.post(
                UPDATE_ER_ENDPOINT_URL,
                headers=UPDATE_ER_REQUEST_HEADERS,
                json=request_body,
            )
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            response_data = response.json()
            print(f"UpdateERTool received response: {response_data}")

            if response_data.get("message") == "Energy resource created successfully":
                return f"Successfully updated client ID {client_id} to PROSUMER. Response: {json.dumps(response_data)}"
            else:
                return f"Failed to update client ID {client_id}. Response: {json.dumps(response_data)}"

        except requests.exceptions.RequestException as e:
            print(f"Error during API call for client_id {client_id}: {e}")
            return f"An error occurred while trying to update the energy resource for client ID {client_id}: {e}"
        except Exception as e:
            print(f"An unexpected error occurred for client_id {client_id}: {e}")
            return f"An unexpected error occurred for client ID {client_id}: {e}"

    async def _arun(self, client_id: int, **kwargs: Any) -> str:
        """Asynchronously updates the energy resource type to PROSUMER for the given client_id."""
        # For a truly async version, you would use a library like aiohttp.
        # For now, this will run synchronously.
        # In a production scenario with many concurrent calls, consider implementing with aiohttp.
        print(f"UpdateERTool (async) attempting to update client_id: {client_id}")
        return self._run(client_id=client_id, **kwargs)
