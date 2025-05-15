UPDATE_ER_ENDPOINT_URL = (
    "https://playground.becknprotocol.io/meter-data-simulator/energy-resources"
)

UPDATE_ER_REQUEST_HEADERS = {"Content-Type": "application/json"}

# Note: The name "Jonathon's Home" and type "PROSUMER" are hardcoded here as per the example.
# If these need to be dynamic, the tool's input schema and logic will need to be adjusted.
UPDATE_ER_REQUEST_BODY_TEMPLATE = {
    "data": {
        "name": "Jonathon's Home",
        "type": "PROSUMER",
        "meter": None,  # Placeholder for client_id
    }
}
