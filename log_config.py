"""
Logging configuration for the trading bot.
Writes structured logs to file and optionally to console.
"""

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "trading_bot.log"

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(level: str = "INFO", verbose: bool = False) -> None:
    """
    Set up root logger.

    Args:
        level:   Log level for the file handler (default INFO).
        verbose: If True, also emit DEBUG logs to stdout.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger("trading_bot")
    root.setLevel(logging.DEBUG)  # capture everything; handlers filter

    # Rotating file handler — keeps last 5 × 5 MB
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    fh.setLevel(numeric_level)
    fh.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FMT))
    root.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(ch)

    root.info("Logging initialised — file: %s  level: %s", LOG_FILE, level)
