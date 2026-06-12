"""
Unit tests for validator and service formatting functions.
Run with: python -m pytest tests/ -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from validator import validate_order, ValidationError, OrderRequest
from service import format_order_summary, format_order_response


# ─── validate_order ───────────────────────────────────────────────────────────

class TestValidateOrder:

    def test_valid_market_buy(self):
        req = validate_order("BTCUSDT", "BUY", "MARKET", 0.001, None, None, "GTC")
        assert req.symbol == "BTCUSDT"
        assert req.side == "BUY"
        assert req.order_type == "MARKET"
        assert req.price is None  # stripped for MARKET

    def test_valid_limit_sell(self):
        req = validate_order("ETHUSDT", "SELL", "LIMIT", 0.1, 2800.0, None, "GTC")
        assert req.price == 2800.0
        assert req.time_in_force == "GTC"

    def test_valid_stop_order(self):
        req = validate_order("BTCUSDT", "BUY", "STOP", 0.001, 30000.0, 29900.0, "GTC")
        assert req.stop_price == 29900.0

    def test_invalid_side(self):
        with pytest.raises(ValidationError, match="side must be one of"):
            validate_order("BTCUSDT", "HOLD", "MARKET", 0.001, None, None, "GTC")

    def test_invalid_order_type(self):
        with pytest.raises(ValidationError, match="order_type must be one of"):
            validate_order("BTCUSDT", "BUY", "TWAP", 0.001, None, None, "GTC")

    def test_negative_quantity(self):
        with pytest.raises(ValidationError, match="quantity must be > 0"):
            validate_order("BTCUSDT", "BUY", "MARKET", -1.0, None, None, "GTC")

    def test_zero_quantity(self):
        with pytest.raises(ValidationError, match="quantity must be > 0"):
            validate_order("BTCUSDT", "BUY", "MARKET", 0, None, None, "GTC")

    def test_limit_missing_price(self):
        with pytest.raises(ValidationError, match="price is required"):
            validate_order("BTCUSDT", "BUY", "LIMIT", 0.001, None, None, "GTC")

    def test_limit_zero_price(self):
        with pytest.raises(ValidationError, match="price is required"):
            validate_order("BTCUSDT", "BUY", "LIMIT", 0.001, 0.0, None, "GTC")

    def test_stop_missing_stop_price(self):
        with pytest.raises(ValidationError, match="stop_price is required"):
            validate_order("BTCUSDT", "BUY", "STOP", 0.001, 30000.0, None, "GTC")

    def test_symbol_normalised_uppercase(self):
        req = validate_order("btcusdt", "buy", "market", 0.001, None, None, "gtc")
        assert req.symbol == "BTCUSDT"
        assert req.side == "BUY"
        assert req.order_type == "MARKET"

    def test_empty_symbol(self):
        with pytest.raises(ValidationError, match="symbol cannot be empty"):
            validate_order("", "BUY", "MARKET", 0.001, None, None, "GTC")


# ─── format helpers ────────────────────────────────────────────────────────────

class TestFormatOrderSummary:

    def _make_req(self, **kwargs):
        defaults = dict(
            symbol="BTCUSDT", side="BUY", order_type="MARKET",
            quantity=0.001, price=None, stop_price=None, time_in_force="GTC",
        )
        defaults.update(kwargs)
        return validate_order(**defaults)

    def test_contains_symbol(self):
        req = self._make_req()
        assert "BTCUSDT" in format_order_summary(req)

    def test_contains_side(self):
        req = self._make_req()
        assert "BUY" in format_order_summary(req)

    def test_limit_shows_price(self):
        req = self._make_req(order_type="LIMIT", price=50000.0)
        assert "50000" in format_order_summary(req)

    def test_market_hides_tif(self):
        req = self._make_req()
        summary = format_order_summary(req)
        assert "TIF" not in summary  # TIF not shown for MARKET


class TestFormatOrderResponse:

    def _make_response(self, **kwargs):
        base = {
            "orderId": 9876543,
            "clientOrderId": "testOrder001",
            "status": "FILLED",
            "origQty": "0.001",
            "executedQty": "0.001",
            "avgPrice": "42000.00",
            "price": "0",
        }
        base.update(kwargs)
        return base

    def test_contains_order_id(self):
        assert "9876543" in format_order_response(self._make_response())

    def test_contains_status(self):
        assert "FILLED" in format_order_response(self._make_response())

    def test_contains_executed_qty(self):
        assert "0.001" in format_order_response(self._make_response())

    def test_partial_fill(self):
        resp = self._make_response(status="PARTIALLY_FILLED", executedQty="0.0005")
        assert "PARTIALLY_FILLED" in format_order_response(resp)
        assert "0.0005" in format_order_response(resp)
