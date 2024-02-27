import json
import logging
from typing import Optional
from urllib.request import Request, urlopen

from shroudstone import __version__

logger = logging.getLogger(__name__)

STORMGATEWORLD = "https://api.stormgateworld.com"
USER_AGENT = f"shroudstone v{__version__}"
"""User-Agent to use in requests to the API"""


def api_request(endpoint: str, **kwargs):
    url = f"{STORMGATEWORLD}{endpoint}"
    logger.debug(f"Making SGW API request: {url}")
    request = Request(
        url,
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
