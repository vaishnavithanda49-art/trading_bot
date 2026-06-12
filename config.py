"""
Configuration — loads API credentials from environment variables or a .env file.
"""

import os
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no dependency on python-dotenv)."""
    if not path.exists():
        return
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


# Auto-load .env from project root
_load_dotenv(Path(__file__).parent / ".env")


def get_credentials() -> tuple[str, str]:
    """
    Return (api_key, api_secret) from environment.
    Raises EnvironmentError if either is missing.
    """
    api_key = os.environ.get("BINANCE_TESTNET_API_KEY", "").strip()
    api_secret = os.environ.get("BINANCE_TESTNET_API_SECRET", "").strip()

    missing = []
    if not api_key:
        missing.append("BINANCE_TESTNET_API_KEY")
    if not api_secret:
        missing.append("BINANCE_TESTNET_API_SECRET")

    if missing:
        raise EnvironmentError(
            f"Missing environment variable(s): {', '.join(missing)}\n"
            "Set them in your shell or in a .env file next to this script."
        )

    return api_key, api_secret
