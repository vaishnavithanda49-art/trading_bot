"""
Web UI server for the Binance Futures Trading Bot.
Run with: python app.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
import logging
import sys
import os

# Add project root to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_credentials
from client import BinanceFuturesClient, BinanceAPIError, NetworkError
from validator import validate_order, ValidationError
from service import OrderService
from log_config import setup_logging

setup_logging(level="INFO")
logger = logging.getLogger("trading_bot.web")

app = Flask(__name__)


def get_service():
    api_key, api_secret = get_credentials()
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    return OrderService(client), client


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/place-order", methods=["POST"])
def place_order():
    data = request.get_json()
    logger.info("Web order request: %s", data)

    try:
        req = validate_order(
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("order_type", ""),
            quantity=float(data.get("quantity", 0)),
            price=float(data["price"]) if data.get("price") else None,
            stop_price=float(data["stop_price"]) if data.get("stop_price") else None,
            time_in_force=data.get("time_in_force", "GTC"),
        )
    except ValidationError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except (ValueError, TypeError) as exc:
        return jsonify({"success": False, "error": f"Invalid input: {exc}"}), 400

    try:
        service, client = get_service()
        result = service.place(req)
        client.close()
        logger.info("Web order success: %s", result)
        return jsonify({"success": True, "order": result})
    except BinanceAPIError as exc:
        logger.error("API error: %s", exc)
        return jsonify({"success": False, "error": f"Binance error {exc.code}: {exc.message}"}), 400
    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        return jsonify({"success": False, "error": f"Network error: {exc}"}), 500
    except EnvironmentError as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/account")
def account():
    try:
        service, client = get_service()
        data = client.get_account()
        client.close()
        usdt = next((a for a in data.get("assets", []) if a["asset"] == "USDT"), {})
        return jsonify({
            "success": True,
            "available": usdt.get("availableBalance", "0"),
            "wallet": usdt.get("walletBalance", "0"),
            "pnl": usdt.get("unrealizedProfit", "0"),
        })
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/price/<symbol>")
def price(symbol):
    try:
        service, client = get_service()
        data = client.get_ticker_price(symbol.upper())
        client.close()
        return jsonify({"success": True, "price": data.get("price", "0"), "symbol": symbol.upper()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    print("\n🚀 Trading Bot Web UI starting...")
    print("👉 Open your browser and go to: http://localhost:5000\n")
    app.run(debug=False, port=5000)
