"""
nifty100_sma_scanner.py
-----------------------
Scans Nifty 100 stocks for SMA 6 / SMA 30 crossovers using Zerodha Kite Connect.

Steps:
    1. Read API key and API secret (from a .env file or environment variables)
    2. Download the Nifty 100 constituents list from NSE
    3. Map each symbol to its NSE instrument token
    4. Fetch daily historical candles
    5. Calculate SMA 6 and SMA 30
    6. Detect the latest Bullish / Bearish crossover
    7. Rank stocks by the most recent crossover

Setup:
    pip install kiteconnect pandas requests

    Create a file called .env next to this script containing:
        KITE_API_KEY=your_api_key
        KITE_API_SECRET=your_api_secret

Run:
    python nifty100_sma_scanner.py

    The script prints a login URL. Log in, then paste the request_token
    (or the whole redirect URL) when asked. The access token is saved to
    access_token.txt so you only need to log in once per day.
"""

import io
import os
import time
from datetime import date, timedelta

import pandas as pd
import requests
from kiteconnect import KiteConnect

# ---------------------------------------------------------------------------
# Settings (change these if you like)
# ---------------------------------------------------------------------------
SHORT_SMA = 6
LONG_SMA = 30
HISTORY_DAYS = 365                  # calendar days of history to download
OUTPUT_CSV = "nifty100_sma_signals.csv"
ACCESS_TOKEN_FILE = "access_token.txt"
ENV_FILE = ".env"

NIFTY100_URLS = [
    "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv",
]

# Kite allows about 3 historical data requests per second
REQUEST_DELAY_SECONDS = 0.35


# ---------------------------------------------------------------------------
# Step 1: Read credentials and log in
# ---------------------------------------------------------------------------
def read_credentials():
    """Read the API key and secret from the .env file, or from environment variables."""
    values = {}

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip('"').strip("'")

    api_key = values.get("KITE_API_KEY") or os.environ.get("KITE_API_KEY")
    api_secret = values.get("KITE_API_SECRET") or os.environ.get("KITE_API_SECRET")

    if not api_key or not api_secret:
        raise SystemExit(
            "API key/secret not found.\n"
            f"Create a {ENV_FILE} file with:\n"
            "    KITE_API_KEY=your_api_key\n"
            "    KITE_API_SECRET=your_api_secret"
        )
    return api_key, api_secret


def load_saved_access_token():
    """Return today's saved access token, or None."""
    if not os.path.exists(ACCESS_TOKEN_FILE):
        return None
    with open(ACCESS_TOKEN_FILE) as f:
        parts = f.read().strip().split(",")
    if len(parts) == 2 and parts[0] == date.today().isoformat():
        return parts[1]
    return None


def save_access_token(token):
    with open(ACCESS_TOKEN_FILE, "w") as f:
        f.write(f"{date.today().isoformat()},{token}")


def extract_request_token(text):
    """Accept either the bare request_token or the full redirect URL."""
    text = text.strip()
    if "request_token=" in text:
        text = text.split("request_token=", 1)[1].split("&", 1)[0]
    return text


def login():
    """Return a logged-in KiteConnect object."""
    api_key, api_secret = read_credentials()
    kite = KiteConnect(api_key=api_key)

    # Try today's saved token first
    saved_token = load_saved_access_token()
    if saved_token:
        kite.set_access_token(saved_token)
        try:
            kite.profile()
            print("Using saved access token from today.")
            return kite
        except Exception:
            print("Saved access token is no longer valid. Please log in again.")

    # Otherwise do a fresh login
    print("\nOpen this URL in your browser and log in:\n")
    print("   ", kite.login_url())
    print("\nAfter logging in you will be redirected to a URL containing 'request_token=...'.")
    raw = input("Paste the request_token (or the full redirect URL) here: ")
    request_token = extract_request_token(raw)

    session = kite.generate_session(request_token, api_secret=api_secret)
    access_token = session["access_token"]
    kite.set_access_token(access_token)
    save_access_token(access_token)
    print("Login successful. Access token saved for today.\n")
    return kite


# ---------------------------------------------------------------------------
# Step 2: Download Nifty 100 constituents
# ---------------------------------------------------------------------------
def download_nifty100():
    """Return a DataFrame with columns: Symbol, Company."""
    headers = {"User-Agent": "Mozilla/5.0"}  # NSE blocks requests without a browser user agent

    for url in NIFTY100_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = [c.strip() for c in df.columns]
            df = df.rename(columns={"Company Name": "Company"})
            df["Symbol"] = df["Symbol"].str.strip()
            print(f"Downloaded {len(df)} Nifty 100 stocks from {url}")
            return df[["Symbol", "Company"]]
        except Exception as e:
            print(f"Could not download from {url}: {e}")

    raise SystemExit("Failed to download the Nifty 100 list from NSE.")


# ---------------------------------------------------------------------------
# Step 3: Map symbols to NSE instrument tokens
# ---------------------------------------------------------------------------
def add_instrument_tokens(kite, stocks):
    """Add an 'instrument_token' column to the stocks DataFrame."""
    instruments = pd.DataFrame(kite.instruments("NSE"))
    instruments = instruments[instruments["instrument_type"] == "EQ"]
    token_map = dict(zip(instruments["tradingsymbol"], instruments["instrument_token"]))

    stocks = stocks.copy()
    stocks["instrument_token"] = stocks["Symbol"].map(token_map)

    missing = stocks[stocks["instrument_token"].isna()]["Symbol"].tolist()
    if missing:
        print(f"Warning: no instrument token found for {missing}")

    stocks = stocks.dropna(subset=["instrument_token"])
    stocks["instrument_token"] = stocks["instrument_token"].astype(int)
    print(f"Mapped {len(stocks)} symbols to instrument tokens.")
    return stocks


# ---------------------------------------------------------------------------
# Step 4: Fetch daily historical data
# ---------------------------------------------------------------------------
def fetch_daily_data(kite, instrument_token):
    """Return a DataFrame of daily candles (date, open, high, low, close, volume)."""
    to_date = date.today()
    from_date = to_date - timedelta(days=HISTORY_DAYS)
    candles = kite.historical_data(instrument_token, from_date, to_date, "day")
    df = pd.DataFrame(candles)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


# ---------------------------------------------------------------------------
# Steps 5 & 6: Calculate SMAs and detect the latest crossover
# ---------------------------------------------------------------------------
def find_latest_crossover(df):
    """
    Return (signal_type, crossover_date, close, sma_short, sma_long) for the
    most recent crossover, or None if there was no crossover in the data.

    Bullish: SMA 6 crosses ABOVE SMA 30
    Bearish: SMA 6 crosses BELOW SMA 30
    """
    df = df.copy()
    df["sma_short"] = df["close"].rolling(SHORT_SMA).mean()
    df["sma_long"] = df["close"].rolling(LONG_SMA).mean()
    df = df.dropna(subset=["sma_short", "sma_long"]).reset_index(drop=True)

    if len(df) < 2:
        return None

    above = df["sma_short"] > df["sma_long"]
    was_above = above.shift(1)

    bullish = above & (was_above == False)   # noqa: E712  (crossed up today)
    bearish = (~above) & (was_above == True)  # noqa: E712  (crossed down today)
    crossovers = df[bullish | bearish]

    if crossovers.empty:
        return None

    last = crossovers.iloc[-1]
    signal = "Bullish" if last["sma_short"] > last["sma_long"] else "Bearish"
    return signal, last["date"], last["close"], last["sma_short"], last["sma_long"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    kite = login()
    stocks = download_nifty100()
    stocks = add_instrument_tokens(kite, stocks)

    results = []
    total = len(stocks)

    for i, row in enumerate(stocks.itertuples(index=False), start=1):
        print(f"[{i}/{total}] {row.Symbol}", end="\r")
        try:
            data = fetch_daily_data(kite, row.instrument_token)
        except Exception as e:
            print(f"\nError fetching {row.Symbol}: {e}")
            continue
        finally:
            time.sleep(REQUEST_DELAY_SECONDS)

        if data.empty:
            continue

        crossover = find_latest_crossover(data)
        if crossover is None:
            continue

        signal, cross_date, close, sma_short, sma_long = crossover
        results.append({
            "Symbol": row.Symbol,
            "Company": row.Company,
            "Signal Type": signal,
            "Cross Over Date": cross_date,
            "Close": round(close, 2),
            f"SMA {SHORT_SMA}": round(sma_short, 2),
            f"SMA {LONG_SMA}": round(sma_long, 2),
        })

    print()  # finish the progress line

    if not results:
        print("No crossovers found.")
        return

    # Step 7: Rank by most recent crossover (newest first)
    signals = pd.DataFrame(results)
    signals = signals.sort_values(["Cross Over Date", "Symbol"], ascending=[False, True])
    signals = signals.reset_index(drop=True)
    signals.insert(0, "Rank", range(1, len(signals) + 1))

    pd.set_option("display.max_rows", None)
    pd.set_option("display.width", 200)
    print(signals.to_string(index=False))

    signals.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(signals)} signals to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
