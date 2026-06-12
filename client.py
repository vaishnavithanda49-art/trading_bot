"""
Binance Futures Testnet API Client
Handles all direct REST interactions with the Binance Futures Testnet.
"""

import hashlib
import hmac
import time
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("trading_bot.client")

BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when Binance returns an error response."""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class NetworkError(Exception):
    """Raised on network/connection failures."""
    pass


class BinanceFuturesClient:
    """
    Low-level REST client for Binance Futures Testnet (USDT-M).
    Handles request signing, headers, and error parsing.
    """

    def __init__(self, api_key: str, api_secret: str, timeout: float = 10.0):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={
                "X-MBX-APIKEY": self.api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=self.timeout,
        )

    def _sign(self, params: dict) -> dict:
        """Append HMAC-SHA256 signature to params."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _handle_response(self, response: httpx.Response) -> dict:
        """Parse response and raise on API errors."""
        logger.debug("Response status: %s", response.status_code)
        logger.debug("Response body: %s", response.text)
        try:
            data = response.json()
        except Exception as exc:
            raise NetworkError(f"Failed to parse JSON response: {response.text}") from exc

        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown error"))

        return data

    def get_exchange_info(self) -> dict:
        """Fetch exchange info (symbol filters, etc.)."""
        logger.info("Fetching exchange info")
        try:
            resp = self._http.get("/fapi/v1/exchangeInfo")
            return self._handle_response(resp)
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error fetching exchange info: {exc}") from exc

    def get_ticker_price(self, symbol: str) -> dict:
        """Get current mark price for a symbol."""
        logger.info("Fetching ticker price for %s", symbol)
        try:
            resp = self._http.get("/fapi/v1/ticker/price", params={"symbol": symbol})
            return self._handle_response(resp)
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error fetching ticker: {exc}") from exc

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        stop_price: Optional[float] = None,
        reduce_only: bool = False,
    ) -> dict:
        """
        Place a futures order.

        Args:
            symbol:        e.g. "BTCUSDT"
            side:          "BUY" or "SELL"
            order_type:    "MARKET", "LIMIT", or "STOP"
            quantity:      order quantity in base asset
            price:         required for LIMIT / STOP orders
            time_in_force: "GTC", "IOC", "FOK" — required for LIMIT
            stop_price:    required for STOP orders
            reduce_only:   only reduce an existing position
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }
        if price is not None:
            params["price"] = price
        if time_in_force is not None:
            params["timeInForce"] = time_in_force
        if stop_price is not None:
            params["stopPrice"] = stop_price
        if reduce_only:
            params["reduceOnly"] = "true"

        params = self._sign(params)

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s",
            side, order_type, symbol, quantity, price,
        )
        logger.debug("Order params: %s", params)

        try:
            resp = self._http.post("/fapi/v1/order", data=params)
            result = self._handle_response(resp)
            logger.info("Order placed successfully: orderId=%s status=%s", result.get("orderId"), result.get("status"))
            return result
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error placing order: {exc}") from exc

    def get_order(self, symbol: str, order_id: int) -> dict:
        """Query a single order by ID."""
        params = self._sign({"symbol": symbol, "orderId": order_id})
        try:
            resp = self._http.get("/fapi/v1/order", params=params)
            return self._handle_response(resp)
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error querying order: {exc}") from exc

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an open order."""
        params = self._sign({"symbol": symbol, "orderId": order_id})
        try:
            resp = self._http.delete("/fapi/v1/order", params=params)
            return self._handle_response(resp)
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error cancelling order: {exc}") from exc

    def get_account(self) -> dict:
        """Fetch account info including balances and positions."""
        params = self._sign({})
        try:
            resp = self._http.get("/fapi/v2/account", params=params)
            return self._handle_response(resp)
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error fetching account: {exc}") from exc

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
