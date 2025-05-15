# API Endpoint for retail search
BASE_URL = "https://bap-ps-client-deg.becknprotocol.io/search"

# Context fields for the search request
CONTEXT_DOMAIN = "deg:retail"
CONTEXT_ACTION = "search"
CONTEXT_LOCATION_COUNTRY_CODE = "USA"
CONTEXT_LOCATION_CITY_CODE = "NANP:628"  # Specific city code from the example
CONTEXT_VERSION = "1.1.0"
CONTEXT_BAP_ID = "bap-ps-network-deg.becknprotocol.io"
CONTEXT_BAP_URI = "https://bap-ps-network-deg.becknprotocol.io/"
# The example request includes specific BPP ID and URI in the search context
CONTEXT_BPP_ID = "bpp-ps-network-deg.becknprotocol.io"
CONTEXT_BPP_URI = "https://bpp-ps-network-deg.becknprotocol.io/"

# Message intent fields for the search request
MESSAGE_INTENT_ITEM_DESCRIPTOR_NAME = "solar"

# API Endpoint for retail select
SELECT_BASE_URL = "https://bap-ps-client-deg.becknprotocol.io/select"

# Context action for select
CONTEXT_ACTION_SELECT = "select"
