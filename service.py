"""
Order service — bridges validated OrderRequest objects to the API client,
formats responses, and handles high-level business logic.
"""

import logging
import time
from typing import Optional

from client import BinanceFuturesClient, BinanceAPIError, NetworkError
from validator import OrderRequest

logger = logging.getLogger("trading_bot.service")


def _fmt_float(value, decimals: int = 8) -> str:
    """Format a numeric string/float without trailing zeros."""
    try:
        return f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value)


def format_order_summary(req: OrderRequest) -> str:
    """Return a human-readable summary of what is about to be placed."""
    lines = [
        "┌─── Order Request ────────────────────────────",
        f"│  Symbol     : {req.symbol}",
        f"│  Side       : {req.side}",
        f"│  Type       : {req.order_type}",
        f"│  Quantity   : {req.quantity}",
    ]
    if req.price:
        lines.append(f"│  Limit Price: {req.price}")
    if req.stop_price:
        lines.append(f"│  Stop Price : {req.stop_price}")
    if req.order_type != "MARKET":
        lines.append(f"│  TIF        : {req.time_in_force}")
    lines.append("└──────────────────────────────────────────────")
    return "\n".join(lines)


def format_order_response(data: dict) -> str:
    """Return a human-readable summary of the API response."""
    order_id   = data.get("orderId", "N/A")
    status     = data.get("status", "N/A")
    exec_qty   = _fmt_float(data.get("executedQty", 0))
    avg_price  = _fmt_float(data.get("avgPrice", data.get("price", 0)))
    orig_qty   = _fmt_float(data.get("origQty", 0))
    client_id  = data.get("clientOrderId", "N/A")
    update_time = data.get("updateTime", "")

    lines = [
        "┌─── Order Response ───────────────────────────",
        f"│  Order ID      : {order_id}",
        f"│  Client OID    : {client_id}",
        f"│  Status        : {status}",
        f"│  Orig Qty      : {orig_qty}",
        f"│  Executed Qty  : {exec_qty}",
        f"│  Avg Price     : {avg_price}",
    ]
    if update_time:
        lines.append(f"│  Update Time   : {update_time}")
    lines.append("└──────────────────────────────────────────────")
    return "\n".join(lines)


class OrderService:
    """High-level order operations."""

    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place(self, req: OrderRequest) -> dict:
        """
        Submit an order and return the raw response dict.
        Raises BinanceAPIError or NetworkError on failure.
        """
        logger.info(
            "Submitting order: %s %s %s qty=%s price=%s",
            req.side, req.order_type, req.symbol, req.quantity, req.price,
        )
        result = self.client.place_order(
            symbol=req.symbol,
            side=req.side,
            order_type=req.order_type,
            quantity=req.quantity,
            price=req.price,
            stop_price=req.stop_price,
            time_in_force=req.time_in_force if req.order_type != "MARKET" else None,
            reduce_only=req.reduce_only,
        )

        # Demo API fills MARKET orders asynchronously — poll until filled
        if req.order_type == "MARKET" and result.get("status") == "NEW":
            logger.info("MARKET order still NEW, polling for final status...")
            for attempt in range(6):
                time.sleep(1)
                try:
                    updated = self.client.get_order(
                        symbol=req.symbol,
                        order_id=result["orderId"],
                    )
                    result = updated
                    logger.info("Poll %d: status=%s", attempt + 1, result.get("status"))
                    if result.get("status") in ("FILLED", "CANCELED", "EXPIRED", "REJECTED"):
                        break
                except Exception as exc:
                    logger.warning("Poll %d failed: %s", attempt + 1, exc)
                    break

        logger.info("Order result: %s", result)
        return result

    def query(self, symbol: str, order_id: int) -> dict:
        return self.client.get_order(symbol=symbol, order_id=order_id)

    def cancel(self, symbol: str, order_id: int) -> dict:
        return self.client.cancel_order(symbol=symbol, order_id=order_id)

    def account_summary(self) -> str:
        """Return a brief account balance summary string."""
        data = self.client.get_account()
        usdt = next(
            (a for a in data.get("assets", []) if a["asset"] == "USDT"), {}
        )
        lines = [
            "┌─── Account Summary ──────────────────────────",
            f"│  Available Balance : {_fmt_float(usdt.get('availableBalance', 0), 2)} USDT",
            f"│  Wallet Balance    : {_fmt_float(usdt.get('walletBalance', 0), 2)} USDT",
            f"│  Unrealised PnL    : {_fmt_float(usdt.get('unrealizedProfit', 0), 4)} USDT",
            "└──────────────────────────────────────────────",
        ]
        return "\n".join(lines)
