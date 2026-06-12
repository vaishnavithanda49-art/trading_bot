"""
Validation helpers for order parameters.
Checks user-supplied values before hitting the API.
"""

from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger("trading_bot.validator")

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP"}
VALID_TIF = {"GTC", "IOC", "FOK"}


class ValidationError(ValueError):
    """Raised when user-supplied order params are invalid."""
    pass


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"
    reduce_only: bool = False


def validate_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float],
    stop_price: Optional[float],
    time_in_force: str,
) -> OrderRequest:
    """
    Validate all order fields and return an OrderRequest dataclass.
    Raises ValidationError with a clear message on any failure.
    """
    errors = []

    # Symbol
    symbol = symbol.strip().upper()
    if not symbol:
        errors.append("symbol cannot be empty")

    # Side
    side = side.strip().upper()
    if side not in VALID_SIDES:
        errors.append(f"side must be one of {sorted(VALID_SIDES)}, got '{side}'")

    # Order type
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        errors.append(f"order_type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'")

    # Quantity
    if quantity <= 0:
        errors.append(f"quantity must be > 0, got {quantity}")

    # Price rules
    if order_type == "LIMIT":
        if price is None or price <= 0:
            errors.append("price is required and must be > 0 for LIMIT orders")

    if order_type == "STOP":
        if price is None or price <= 0:
            errors.append("price (limit price) is required and must be > 0 for STOP orders")
        if stop_price is None or stop_price <= 0:
            errors.append("stop_price is required and must be > 0 for STOP orders")

    if order_type == "MARKET" and price is not None:
        logger.warning("price is ignored for MARKET orders")

    # Time-in-force
    time_in_force = time_in_force.strip().upper()
    if order_type in ("LIMIT", "STOP") and time_in_force not in VALID_TIF:
        errors.append(f"time_in_force must be one of {sorted(VALID_TIF)}, got '{time_in_force}'")

    if errors:
        raise ValidationError("\n  • ".join(["Validation failed:"] + errors))

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price if order_type != "MARKET" else None,
        stop_price=stop_price,
        time_in_force=time_in_force,
    )
