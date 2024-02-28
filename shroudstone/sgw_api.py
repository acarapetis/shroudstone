from shroudstone.stormgateworld import ApiClient
from shroudstone.stormgateworld.api import players_api, matches_api
from shroudstone import __version__

USER_AGENT = f"shroudstone v{__version__}"
"""User-Agent to use in requests to the API"""

client = ApiClient()
client.user_agent = USER_AGENT

PlayersApi = players_api.PlayersApi(api_client=client)
