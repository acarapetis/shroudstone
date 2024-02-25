import json
from typing import Optional
from urllib.request import urlopen, Request
from shroudstone import __version__

STORMGATEWORLD = "https://api.stormgateworld.com"
USER_AGENT = f"shroudstone v{__version__}"
"""User-Agent to use in requests to the API"""

def api_request(endpoint: str, **kwargs):
    request = Request(
        f"{STORMGATEWORLD}{endpoint}",
        headers={"User-Agent": USER_AGENT},
        **kwargs,
    )
    with urlopen(request) as f:
        return json.load(f)


def get_nickname(player_id: str) -> Optional[str]:
    try:
        return api_request(f"/v0/players/{player_id}")["nickname"]
    except Exception:
        return None
