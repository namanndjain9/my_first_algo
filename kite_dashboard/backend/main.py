"""
Kite Dashboard - FastAPI backend
--------------------------------
Handles the Zerodha Kite Connect login and talks to Kite on behalf of the browser.

The access token is saved in `.kite_session.json` (next to this file) and is
NEVER sent to the browser. Because it lives in a file, it survives backend
restarts and `--reload`, so you only log in once per day during development.

Run:
    uvicorn main:app --reload --port 8000
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from kiteconnect import KiteConnect
from kiteconnect import exceptions as kite_exceptions
from pydantic import BaseModel, Field, model_validator

from signals import run_scan

SESSION_FILE = Path(__file__).parent / ".kite_session.json"

app = FastAPI(title="Kite Dashboard API")


# ---------------------------------------------------------------------------
# Session storage (a small JSON file on the backend)
# ---------------------------------------------------------------------------
def load_session():
    """Return the saved session dict, or None if there isn't one."""
    if not SESSION_FILE.exists():
        return None
    try:
        return json.loads(SESSION_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def save_session(api_key, access_token, user_id):
    data = {
        "api_key": api_key,
        "access_token": access_token,
        "user_id": user_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    SESSION_FILE.write_text(json.dumps(data, indent=2))
    try:
        SESSION_FILE.chmod(0o600)  # owner-only on macOS/Linux; ignored on Windows
    except OSError:
        pass


def clear_session():
    SESSION_FILE.unlink(missing_ok=True)


def get_kite():
    """Return a KiteConnect client using the saved access token, or raise 401."""
    session = load_session()
    if not session:
        raise HTTPException(status_code=401, detail="Not logged in.")
    kite = KiteConnect(api_key=session["api_key"])
    kite.set_access_token(session["access_token"])
    return kite


def call_kite(fn):
    """Run a Kite API call and turn Kite errors into clean HTTP errors."""
    try:
        return fn()
    except HTTPException:
        raise
    except kite_exceptions.TokenException:
        # Kite tokens expire every morning (~6 AM IST) - force a fresh login.
        clear_session()
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except kite_exceptions.KiteException as e:
        raise HTTPException(status_code=502, detail=f"Kite error: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Kite: {e}")


def extract_request_token(text):
    """Accept either the bare request_token or the full redirect URL."""
    text = text.strip()
    if "request_token=" in text:
        text = text.split("request_token=", 1)[1].split("&", 1)[0]
    return text


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    api_key: str = Field(min_length=1)
    api_secret: str = Field(min_length=1)
    request_token: str = Field(min_length=1)


@app.get("/api/auth/status")
def auth_status():
    """Tell the frontend whether a valid saved session exists."""
    if not load_session():
        return {"logged_in": False}
    try:
        profile = call_kite(lambda: get_kite().profile())
    except HTTPException as e:
        return {"logged_in": False, "message": e.detail}
    return {"logged_in": True, "user_name": profile.get("user_name")}


@app.post("/api/auth/login")
def login(body: LoginRequest):
    """Exchange the request token for an access token and save it on the backend."""
    api_key = body.api_key.strip()
    kite = KiteConnect(api_key=api_key)
    try:
        session = kite.generate_session(
            extract_request_token(body.request_token),
            api_secret=body.api_secret.strip(),
        )
    except kite_exceptions.TokenException:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired request token. Request tokens work only once "
                   "and expire within a few minutes - log in to Kite again for a new one.",
        )
    except kite_exceptions.KiteException as e:
        raise HTTPException(status_code=400, detail=f"Kite login failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Kite: {e}")

    save_session(api_key, session["access_token"], session.get("user_id"))
    # Note: the access token is deliberately NOT included in the response.
    return {"logged_in": True, "user_name": session.get("user_name")}


@app.post("/api/auth/logout")
def logout():
    """Invalidate the token at Kite (best effort) and delete the saved session."""
    if load_session():
        try:
            get_kite().invalidate_access_token()
        except Exception:
            pass
    clear_session()
    return {"logged_in": False}


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------
@app.get("/api/profile")
def profile():
    data = call_kite(lambda: get_kite().profile())
    return {
        "user_name": data.get("user_name"),
        "user_id": data.get("user_id"),
        "products": data.get("products", []),
        "exchanges": data.get("exchanges", []),
    }


class SignalsRequest(BaseModel):
    short_sma: int = Field(default=6, ge=1, le=200)
    long_sma: int = Field(default=30, ge=2, le=400)
    lookback_days: int = Field(default=365, ge=30, le=2000)  # Kite allows up to 2000 days of daily data
    max_stocks: int = Field(default=100, ge=1, le=100)

    @model_validator(mode="after")
    def check_values(self):
        if self.long_sma <= self.short_sma:
            raise ValueError("Long SMA must be greater than Short SMA.")
        # Roughly 5 trading days per 7 calendar days
        if self.lookback_days * 5 / 7 < self.long_sma + 2:
            raise ValueError(
                f"Lookback Days is too short for a {self.long_sma}-day SMA. "
                f"Use at least {int((self.long_sma + 2) * 7 / 5) + 10} days."
            )
        return self


@app.post("/api/signals")
def signals(body: SignalsRequest):
    """Scan Nifty 100 stocks for the latest SMA crossover."""
    def scan():
        try:
            return run_scan(get_kite(), body.short_sma, body.long_sma,
                            body.lookback_days, body.max_stocks)
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))

    return {**call_kite(scan), "params": body.model_dump()}
