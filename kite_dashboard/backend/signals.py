"""
Nifty 100 SMA crossover scanner.

Steps:
    1. Load Nifty 100 symbols from the official Nifty Indices CSV
    2. Map symbols to Kite NSE instrument tokens
    3. Fetch daily historical candles
    4. Calculate the short and long SMA
    5. Detect the latest bullish / bearish crossover
    6. Rank stocks by the most recent crossover date first
"""

import io
import time
from datetime import date, timedelta

import pandas as pd
import requests

NIFTY100_URLS = [
    "https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv",  # official source
    "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",  # backup mirror
]

# Kite allows about 3 historical data requests per second
REQUEST_DELAY_SECONDS = 0.35

# Simple in-memory caches (refreshed once per day)
_cache = {"day": None, "nifty100": None, "tokens": None}


def _reset_cache_if_new_day():
    if _cache["day"] != date.today():
        _cache.update({"day": date.today(), "nifty100": None, "tokens": None})


# ---------------------------------------------------------------------------
# Step 1: Nifty 100 constituents
# ---------------------------------------------------------------------------
def load_nifty100():
    """Return a DataFrame with columns: Symbol, Company."""
    _reset_cache_if_new_day()
    if _cache["nifty100"] is not None:
        return _cache["nifty100"]

    headers = {"User-Agent": "Mozilla/5.0"}  # these sites block requests without a browser user agent
    errors = []
    for url in NIFTY100_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = [c.strip() for c in df.columns]
            df = df.rename(columns={"Company Name": "Company"})
            df["Symbol"] = df["Symbol"].str.strip()
            _cache["nifty100"] = df[["Symbol", "Company"]]
            return _cache["nifty100"]
        except Exception as e:
            errors.append(f"{url}: {e}")

    raise RuntimeError("Could not download the Nifty 100 list. " + " | ".join(errors))


# ---------------------------------------------------------------------------
# Step 2: Symbol -> instrument token
# ---------------------------------------------------------------------------
def load_token_map(kite):
    """Return {tradingsymbol: instrument_token} for NSE equities."""
    _reset_cache_if_new_day()
    if _cache["tokens"] is None:
        instruments = kite.instruments("NSE")
        _cache["tokens"] = {
            i["tradingsymbol"]: i["instrument_token"]
            for i in instruments
            if i.get("instrument_type") == "EQ"
        }
    return _cache["tokens"]


# ---------------------------------------------------------------------------
# Steps 3-5: candles, SMAs, crossover
# ---------------------------------------------------------------------------
def fetch_daily_candles(kite, instrument_token, lookback_days):
    to_date = date.today()
    from_date = to_date - timedelta(days=lookback_days)
    df = pd.DataFrame(kite.historical_data(instrument_token, from_date, to_date, "day"))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def find_latest_crossover(df, short_sma, long_sma):
    """
    Return the most recent crossover as a dict, or None if there is none.

    Bullish: short SMA crosses ABOVE the long SMA
    Bearish: short SMA crosses BELOW the long SMA
    """
    df = df.copy()
    df["sma_short"] = df["close"].rolling(short_sma).mean()
    df["sma_long"] = df["close"].rolling(long_sma).mean()
    df = df.dropna(subset=["sma_short", "sma_long"]).reset_index(drop=True)
    if len(df) < 2:
        return None

    above = df["sma_short"] > df["sma_long"]
    was_above = above.shift(1)
    crossed = (above & (was_above == False)) | (~above & (was_above == True))  # noqa: E712
    crossovers = df[crossed]
    if crossovers.empty:
        return None

    last = crossovers.iloc[-1]
    return {
        "type": "Bullish" if last["sma_short"] > last["sma_long"] else "Bearish",
        "date": last["date"],
        "close": round(float(last["close"]), 2),
        "sma_short": round(float(last["sma_short"]), 2),
        "sma_long": round(float(last["sma_long"]), 2),
    }


# ---------------------------------------------------------------------------
# Step 6: run the whole scan
# ---------------------------------------------------------------------------
def run_scan(kite, short_sma, long_sma, lookback_days, max_stocks):
    stocks = load_nifty100().head(max_stocks)
    token_map = load_token_map(kite)

    signals = []
    no_crossover = []
    skipped = []  # (symbol, reason)

    for row in stocks.itertuples(index=False):
        token = token_map.get(row.Symbol)
        if token is None:
            skipped.append({"ticker": row.Symbol, "reason": "No NSE instrument token"})
            continue

        try:
            candles = fetch_daily_candles(kite, token, lookback_days)
        except Exception as e:
            # Token errors mean the whole session is bad - stop and let the caller handle it
            if type(e).__name__ == "TokenException":
                raise
            skipped.append({"ticker": row.Symbol, "reason": str(e)})
            continue
        finally:
            time.sleep(REQUEST_DELAY_SECONDS)

        if len(candles) <= long_sma:
            skipped.append({"ticker": row.Symbol, "reason": f"Only {len(candles)} candles"})
            continue

        crossover = find_latest_crossover(candles, short_sma, long_sma)
        if crossover is None:
            no_crossover.append(row.Symbol)
            continue

        signals.append({"ticker": row.Symbol, "company": row.Company, **crossover})

    # Most recent crossover first; ties broken alphabetically
    signals.sort(key=lambda s: s["ticker"])
    signals.sort(key=lambda s: s["date"], reverse=True)
    for rank, signal in enumerate(signals, start=1):
        signal["rank"] = rank
        signal["date"] = signal["date"].isoformat()

    return {
        "signals": signals,
        "scanned": len(stocks),
        "no_crossover": no_crossover,
        "skipped": skipped,
    }
