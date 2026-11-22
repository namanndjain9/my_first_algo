# Kite Dashboard

A React + Vite frontend with a Python FastAPI backend for Zerodha Kite Connect.

- Log in with your **API Key**, **API Secret** and **Request Token**
- The backend creates the **access token** and keeps it in `backend/.kite_session.json`.
  The token is **never sent to the browser**.
- The saved token is reused, so restarting the servers or editing code doesn't log you out.
  Kite expires tokens every morning (around 6 AM IST), so you log in once a day.
- The dashboard has tabs:
  - **User**: your name, user ID, products and exchanges
  - **Signals**: a Nifty 100 SMA crossover scanner (see below)

```
kite_dashboard/
├── backend/
│   ├── main.py              FastAPI app (login, logout, status, profile, signals)
│   ├── signals.py           Nifty 100 SMA crossover scanner
│   └── requirements.txt
└── frontend/
    ├── vite.config.js       sends /api/* to the backend
    └── src/
        ├── theme.css        ← colors, fonts, radius: customize here
        ├── styles.css       layout and components
        ├── api.js           all backend calls
        ├── App.jsx          routing (login ↔ dashboard)
        ├── pages/           LoginPage, DashboardPage
        └── tabs/            dashboard tabs (index.js lists them)
```

## Requirements

- Python 3.10+
- Node.js 18+
- A Kite Connect app from https://developers.kite.trade

## 1. One-time Kite app setting (recommended)

In the Kite developer console, set your app's **Redirect URL** to:

```
http://localhost:5173/login
```

After you log in to Kite, it sends you back to the login page and the **Request Token is filled in for you**.
If you use a different redirect URL, copy the `request_token=...` value from the address bar and paste it in.
You can also paste the whole URL.

## 2. Start the backend (terminal 1)

```bash
cd kite_dashboard/backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/docs

## 3. Start the frontend (terminal 2)

```bash
cd kite_dashboard/frontend
npm install
npm run dev
```

Open http://localhost:5173

## 4. Log in

1. Enter your **API Key** and **API Secret**.
2. Click **"Log in to Kite to get a request token"**. Log in at Zerodha.
3. When you land back on the page, the Request Token is filled in. Click **Login**.

Request tokens work **only once** and expire after a few minutes. If login fails, get a fresh one.

## Signals tab

The Signals tab scans the Nifty 100 for moving-average crossovers:

1. Loads the Nifty 100 list from the official Nifty Indices CSV. It falls back to the NSE archive if that fails.
2. Maps each symbol to its Kite NSE instrument token.
3. Downloads daily candles for the **Lookback Days** you choose.
4. Calculates the **Short SMA** (default 6) and **Long SMA** (default 30).
5. Finds each stock's latest crossover:
   - **Bullish**: the short SMA crosses above the long SMA
   - **Bearish**: the short SMA crosses below the long SMA
6. Ranks stocks with the newest crossover first.

| Input | Meaning |
|---|---|
| Short SMA | Fast moving average, in trading days |
| Long SMA | Slow moving average. Must be bigger than Short SMA |
| Lookback Days | Calendar days of history to download (30–2000). Use more days to find older crossovers |
| Max Stocks | How many Nifty 100 stocks to scan (1–100) |

Kite allows about 3 history requests per second, so a full 100-stock scan takes about **40 seconds**.
Stocks with no crossover in the lookback window aren't listed. The table toolbar shows how many there were.
Your Kite Connect plan must include **historical data** access.

## Customizing

- **Colors / fonts**: edit `frontend/src/theme.css`. Every color in the app comes from those variables.
- **Add a tab**: create `frontend/src/tabs/HoldingsTab.jsx`, then add it to the list in `frontend/src/tabs/index.js`.
- **Add a backend endpoint**: in `backend/main.py`, copy the `/api/profile` function.
  For example, return `call_kite(lambda: get_kite().holdings())`. Then add a function for it in `frontend/src/api.js`.

## Security notes

- `backend/.kite_session.json` holds your live access token. Don't share it or commit it. It's in `.gitignore`.
- The API secret is used once to create the token and is never saved.
- The browser remembers only your API key, for convenience.
- The backend listens on `127.0.0.1` only. Don't expose it to the internet as is, because it has no user authentication.
- **Logout** cancels the token at Kite and deletes the session file.
