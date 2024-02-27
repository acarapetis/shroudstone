import logging
from rich.console import Console
from rich.logging import RichHandler
from shroudstone.gui import app

console = Console(stderr=True)
logging.captureWarnings(True)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, show_path=False, show_time=False)],
)
logger = logging.getLogger(__name__)

app.run()
