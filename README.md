# 📈 Binance Futures Testnet Trading Bot

A clean, structured Python CLI application for placing and managing orders on the **Binance Futures Testnet (USDT-M)**.

---

## Architecture

```
trading_bot/
├── main.py          # CLI entry point (argparse)
├── client.py        # API client layer — all HTTP/REST logic
├── service.py       # Business logic, formatting, OrderService
├── validator.py     # Input validation, OrderRequest dataclass
├── config.py        # Credential loading from env / .env file
├── log_config.py    # Rotating file + console logging setup
├── logs/
│   └── trading_bot.log
├── tests/
│   └── test_bot.py  # 20 unit tests (pytest)
├── .env.example
├── requirements.txt
└── README.md
```

**Layer separation:**
- `client.py` — knows only about HTTP, signing, and Binance response shapes
- `service.py` — knows only about `OrderRequest` and formatting; calls `client.py`
- `main.py` — knows only about the CLI; calls `validator.py` and `service.py`

---

## Setup

### 1. Get Testnet credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com) and log in with GitHub.
2. Go to **Account → API Management → Create API Key**.
3. Copy your **API Key** and **Secret Key**.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Only one dependency: `httpx` (modern async-capable HTTP client).

### 3. Configure credentials

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
# then edit .env:
# BINANCE_TESTNET_API_KEY=your_key_here
# BINANCE_TESTNET_API_SECRET=your_secret_here
```

Or export them directly:

```bash
export BINANCE_TESTNET_API_KEY=your_key_here
export BINANCE_TESTNET_API_SECRET=your_secret_here
```

---

## Usage

All commands support `--help`:

```bash
python main.py --help
python main.py order --help
```

### Place a MARKET order

```bash
python main.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

### Place a LIMIT order

```bash
python main.py order --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 72000
```

### Place a STOP order *(bonus: 3rd order type)*

```bash
python main.py order \
  --symbol ETHUSDT --side BUY --type STOP \
  --qty 0.01 --price 3600 --stop-price 3580
```

### Skip confirmation prompt (`-y`)

```bash
python main.py order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 -y
```

### Query an order

```bash
python main.py query --symbol BTCUSDT --order-id 3953907681
```

### Cancel an order

```bash
python main.py cancel --symbol BTCUSDT --order-id 3953912047
```

### View account balance

```bash
python main.py account
```

### Debug / verbose mode

```bash
python main.py -v --log-level DEBUG order --symbol BTCUSDT --side BUY --type MARKET --qty 0.001 -y
```

---

## Sample Output

### MARKET BUY

```
┌─── Order Request ────────────────────────────
│  Symbol     : BTCUSDT
│  Side       : BUY
│  Type       : MARKET
│  Quantity   : 0.001
└──────────────────────────────────────────────
┌─── Order Response ───────────────────────────
│  Order ID      : 3953907681
│  Client OID    : x-Cb7ytekJ8c15e4d3b5db
│  Status        : FILLED
│  Orig Qty      : 0.001
│  Executed Qty  : 0.001
│  Avg Price     : 67823.5
└──────────────────────────────────────────────

✅  Order placed — ID: 3953907681  Status: FILLED
```

### LIMIT SELL

```
┌─── Order Request ────────────────────────────
│  Symbol     : BTCUSDT
│  Side       : SELL
│  Type       : LIMIT
│  Quantity   : 0.001
│  Limit Price: 72000.0
│  TIF        : GTC
└──────────────────────────────────────────────
┌─── Order Response ───────────────────────────
│  Order ID      : 3953912047
│  Status        : NEW
│  Orig Qty      : 0.001
│  Executed Qty  : 0
│  Avg Price     : 0
└──────────────────────────────────────────────

✅  Order placed — ID: 3953912047  Status: NEW
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

All 20 tests cover input validation (edge cases, normalisation, error paths) and output formatting.

---

## Logging

Logs are written to `logs/trading_bot.log` (rotating, 5 MB × 5 files).

Each log entry includes timestamp, level, module, and message. API responses are logged at DEBUG level; order lifecycle events at INFO; errors at ERROR.

```
2024-06-11T09:12:01 | INFO  | trading_bot.client | Placing BUY MARKET order | symbol=BTCUSDT qty=0.001 price=None
2024-06-11T09:12:01 | INFO  | trading_bot.client | Order placed successfully: orderId=3953907681 status=FILLED
```

---

## Assumptions

- Testnet base URL: `https://testnet.binancefuture.com` (USDT-M futures only)
- All timestamps use server-side Unix ms (no clock sync required beyond reasonable skew)
- `STOP` order type = Stop-Limit on Binance Futures (requires both `price` and `stopPrice`)
- Default time-in-force for LIMIT/STOP orders is `GTC` (Good Till Cancelled)
- Positions use `BOTH` side (one-way mode) — the default for new testnet accounts

---

## Bonus Features Implemented

- ✅ **Third order type**: `STOP` (Stop-Limit) — trigger price + limit price
- ✅ **Enhanced CLI UX**: confirmation prompt before every order (bypass with `-y`), box-drawing output, colour-coded success/error markers
