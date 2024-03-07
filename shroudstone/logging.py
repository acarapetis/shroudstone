import logging
from rich.console import Console
from rich.logging import RichHandler


_logging_configured: bool = False

def configure_logging(debug: bool = False):
    global _logging_configured
    if not _logging_configured:
        _logging_configured = True
        level = logging.DEBUG if debug else logging.INFO
        console = Console(stderr=True)
        logging.captureWarnings(True)
        logging.basicConfig(
            level=level,
            format="%(name)s: %(message)s" if debug else "%(message)s",
            handlers=[RichHandler(console=console, show_path=False, show_time=False)],
        )
