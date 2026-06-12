#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI Entry Point

Usage examples:
  python main.py order --symbol BTCUSDT --side BUY  --type MARKET --qty 0.001
  python main.py order --symbol BTCUSDT --side SELL --type LIMIT  --qty 0.001 --price 50000
  python main.py order --symbol ETHUSDT --side BUY  --type STOP   --qty 0.01  --price 2900 --stop-price 2950
  python main.py query --symbol BTCUSDT --order-id 123456
  python main.py cancel --symbol BTCUSDT --order-id 123456
  python main.py account
"""

import argparse
import sys
import logging

from log_config import setup_logging
from config import get_credentials
from client import BinanceFuturesClient, BinanceAPIError, NetworkError
from validator import validate_order, ValidationError
from service import OrderService, format_order_summary, format_order_response


logger = logging.getLogger("trading_bot.cli")

# ─── helpers ──────────────────────────────────────────────────────────────────

def _print_success(msg: str) -> None:
    print(f"\n✅  {msg}\n")

def _print_error(msg: str) -> None:
    print(f"\n❌  {msg}\n", file=sys.stderr)

def _print_info(msg: str) -> None:
    print(msg)


# ─── sub-command handlers ──────────────────────────────────────────────────────

def cmd_order(args: argparse.Namespace, service: OrderService) -> int:
    """Handle the 'order' sub-command."""
    try:
        req = validate_order(
            symbol=args.symbol,
            side=args.side,
            order_type=args.type,
            quantity=args.qty,
            price=args.price,
            stop_price=args.stop_price,
            time_in_force=args.tif,
        )
    except ValidationError as exc:
        logger.error("Validation error: %s", exc)
        _print_error(str(exc))
        return 1

    _print_info(format_order_summary(req))

    # Confirm if not --yes flag
    if not args.yes:
        try:
            answer = input("Proceed with this order? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer not in ("y", "yes"):
            _print_info("Order cancelled by user.")
            logger.info("Order cancelled by user before submission")
            return 0

    try:
        result = service.place(req)
    except ValidationError as exc:
        logger.error("Validation error: %s", exc)
        _print_error(str(exc))
        return 1
    except BinanceAPIError as exc:
        logger.error("API error placing order: %s", exc)
        _print_error(f"API error — code {exc.code}: {exc.message}")
        return 1
    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        _print_error(f"Network error: {exc}")
        return 1

    _print_info(format_order_response(result))
    _print_success(f"Order placed — ID: {result.get('orderId')}  Status: {result.get('status')}")
    return 0


def cmd_query(args: argparse.Namespace, service: OrderService) -> int:
    """Handle the 'query' sub-command."""
    try:
        result = service.query(symbol=args.symbol.upper(), order_id=args.order_id)
    except BinanceAPIError as exc:
        logger.error("API error querying order: %s", exc)
        _print_error(f"API error — code {exc.code}: {exc.message}")
        return 1
    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        _print_error(f"Network error: {exc}")
        return 1

    _print_info(format_order_response(result))
    return 0


def cmd_cancel(args: argparse.Namespace, service: OrderService) -> int:
    """Handle the 'cancel' sub-command."""
    if not args.yes:
        try:
            answer = input(f"Cancel order {args.order_id} on {args.symbol}? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "n"
        if answer not in ("y", "yes"):
            _print_info("Cancellation aborted.")
            return 0

    try:
        result = service.cancel(symbol=args.symbol.upper(), order_id=args.order_id)
    except BinanceAPIError as exc:
        logger.error("API error cancelling order: %s", exc)
        _print_error(f"API error — code {exc.code}: {exc.message}")
        return 1
    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        _print_error(f"Network error: {exc}")
        return 1

    _print_info(format_order_response(result))
    _print_success(f"Order {result.get('orderId')} cancelled — Status: {result.get('status')}")
    return 0


def cmd_account(args: argparse.Namespace, service: OrderService) -> int:
    """Handle the 'account' sub-command."""
    try:
        summary = service.account_summary()
    except BinanceAPIError as exc:
        logger.error("API error fetching account: %s", exc)
        _print_error(f"API error — code {exc.code}: {exc.message}")
        return 1
    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        _print_error(f"Network error: {exc}")
        return 1

    _print_info(summary)
    return 0


# ─── argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level for the file handler (default: INFO)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Also print DEBUG logs to console",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── order ──
    p_order = sub.add_parser("order", help="Place a new order")
    p_order.add_argument("--symbol",     required=True, help="Trading pair, e.g. BTCUSDT")
    p_order.add_argument("--side",       required=True, choices=["BUY", "SELL"],
                         type=str.upper, help="Order side")
    p_order.add_argument("--type",       required=True, choices=["MARKET", "LIMIT", "STOP"],
                         type=str.upper, help="Order type")
    p_order.add_argument("--qty",        required=True, type=float, help="Order quantity")
    p_order.add_argument("--price",      type=float, default=None,
                         help="Limit price (required for LIMIT / STOP)")
    p_order.add_argument("--stop-price", type=float, default=None, dest="stop_price",
                         help="Stop trigger price (required for STOP orders)")
    p_order.add_argument("--tif",        default="GTC", choices=["GTC", "IOC", "FOK"],
                         help="Time-in-force for LIMIT/STOP orders (default: GTC)")
    p_order.add_argument("-y", "--yes",  action="store_true",
                         help="Skip confirmation prompt")

    # ── query ──
    p_query = sub.add_parser("query", help="Query an existing order")
    p_query.add_argument("--symbol",   required=True)
    p_query.add_argument("--order-id", required=True, type=int, dest="order_id")

    # ── cancel ──
    p_cancel = sub.add_parser("cancel", help="Cancel an open order")
    p_cancel.add_argument("--symbol",   required=True)
    p_cancel.add_argument("--order-id", required=True, type=int, dest="order_id")
    p_cancel.add_argument("-y", "--yes", action="store_true",
                          help="Skip confirmation prompt")

    # ── account ──
    sub.add_parser("account", help="Show account balance summary")

    return parser


# ─── entry point ──────────────────────────────────────────────────────────────

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    setup_logging(level=args.log_level, verbose=args.verbose)
    logger.info("Command: %s  args: %s", args.command, vars(args))

    try:
        api_key, api_secret = get_credentials()
    except EnvironmentError as exc:
        _print_error(str(exc))
        return 1

    with BinanceFuturesClient(api_key=api_key, api_secret=api_secret) as client:
        service = OrderService(client)

        dispatch = {
            "order":   cmd_order,
            "query":   cmd_query,
            "cancel":  cmd_cancel,
            "account": cmd_account,
        }
        handler = dispatch[args.command]
        return handler(args, service)


if __name__ == "__main__":
    sys.exit(main())
