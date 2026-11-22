# My First Algo

Tools for scanning Nifty 100 stocks for **SMA crossovers** using the [Zerodha Kite Connect](https://kite.trade) API.

There are two ways to use it:

| | What it is | Best for |
|---|---|---|
| [`nifty100_sma_scanner.py`](nifty100_sma_scanner.py) | A single Python script you run in the terminal | A quick scan that saves results to a CSV |
| [`kite_dashboard/`](kite_dashboard/) | A web dashboard (React frontend + FastAPI backend) | Logging in and running scans from the browser with adjustable settings |

## How the scan works

1. Downloads the current Nifty 100 list from Nifty Indices (with an NSE archive backup).
2. Maps each symbol to its Kite NSE instrument token.
3. Fetches daily candles for each stock.
4. Calculates a **short SMA** (default 6 days) and a **long SMA** (default 30 days).
5. Finds each stock's latest crossover:
   - **Bullish**: the short SMA crosses above the long SMA
   - **Bearish**: the short SMA crosses below the long SMA
6. Ranks stocks with the most recent crossover first.

Kite allows about 3 history requests per second, so a full 100-stock scan takes about 40 seconds.

## Requirements

- Python 3.10+
- Node.js 18+ (only for the dashboard)
- A Kite Connect app from https://developers.kite.trade with **historical data** access

## Option 1: Command-line scanner

```bash
pip install kiteconnect pandas requests
```

Create a `.env` file in the project folder:

```
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
```

Run it:

```bash
python nifty100_sma_scanner.py
```

The script prints a Kite login URL. Log in, then paste the `request_token`, or the whole redirect URL, when it asks.
Results are saved to `nifty100_sma_signals.csv`.
The access token is saved to `access_token.txt`, so you only log in once per day. Kite expires tokens around 6 AM IST.

To change the SMA lengths or the amount of history, edit the settings at the top of the script.

## Option 2: Web dashboard

See [`kite_dashboard/README.md`](kite_dashboard/README.md) for full setup. In short:

```bash
# Terminal 1: backend
cd kite_dashboard/backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2: frontend
cd kite_dashboard/frontend
npm install
npm run dev
```

Then open http://localhost:5173.

## Project structure

```
my_first_algo/
├── nifty100_sma_scanner.py   Standalone command-line scanner
└── kite_dashboard/
    ├── backend/              FastAPI app: Kite login, profile, signals scan
    └── frontend/             React + Vite dashboard
```

## Security

These files hold your credentials or live tokens. They are listed in `.gitignore` and must **never** be committed:

- `.env`: API key and secret
- `access_token.txt`: the scanner's saved access token
- `kite_dashboard/backend/.kite_session.json`: the dashboard's saved access token
- `credentials.txt`

## Disclaimer

This project is for learning only. It is not financial advice. Check any signal yourself before trading.
