import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

const API_KEY_STORAGE = "kite_api_key"; // only the API key is remembered, never the secret

function readSavedApiKey() {
  try {
    return localStorage.getItem(API_KEY_STORAGE) || "";
  } catch {
    return "";
  }
}

export default function LoginPage({ onLogin, notice }) {
  const navigate = useNavigate();
  const [apiKey, setApiKey] = useState(readSavedApiKey);
  const [apiSecret, setApiSecret] = useState("");
  const [requestToken, setRequestToken] = useState("");
  const [error, setError] = useState(notice || "");
  const [loading, setLoading] = useState(false);

  // If Kite redirected back here (?request_token=...), fill it in automatically.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("request_token");
    if (token) {
      setRequestToken(token);
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);

  const kiteLoginUrl = apiKey.trim()
    ? `https://kite.zerodha.com/connect/login?v=3&api_key=${encodeURIComponent(apiKey.trim())}`
    : null;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const status = await api.login({
        api_key: apiKey.trim(),
        api_secret: apiSecret.trim(),
        request_token: requestToken.trim(),
      });
      try {
        localStorage.setItem(API_KEY_STORAGE, apiKey.trim());
      } catch {
        /* storage unavailable - not important */
      }
      onLogin(status);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = apiKey.trim() && apiSecret.trim() && requestToken.trim() && !loading;

  return (
    <div className="center-screen">
      <form className="card login-card" onSubmit={handleSubmit}>
        <div className="login-header">
          <div className="brand-mark">K</div>
          <h1>Kite Dashboard</h1>
          <p className="muted">Sign in with your Kite Connect app credentials</p>
        </div>

        <label className="field">
          <span>API Key</span>
          <input
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Your Kite Connect API key"
            autoComplete="off"
            spellCheck={false}
          />
        </label>

        <label className="field">
          <span>API Secret</span>
          <input
            type="password"
            value={apiSecret}
            onChange={(e) => setApiSecret(e.target.value)}
            placeholder="Your Kite Connect API secret"
            autoComplete="off"
          />
        </label>

        <label className="field">
          <span>Request Token</span>
          <input
            value={requestToken}
            onChange={(e) => setRequestToken(e.target.value)}
            placeholder="Paste request_token or the full redirect URL"
            autoComplete="off"
            spellCheck={false}
          />
          <small className="muted">
            {kiteLoginUrl ? (
              <>
                Don't have one?{" "}
                <a href={kiteLoginUrl} target="_blank" rel="noreferrer">
                  Log in to Kite to get a request token ↗
                </a>
              </>
            ) : (
              "Enter your API key to get a Kite login link."
            )}
          </small>
        </label>

        {error && <div className="alert alert-error">{error}</div>}

        <button className="btn btn-primary btn-block" type="submit" disabled={!canSubmit}>
          {loading ? "Logging in…" : "Login"}
        </button>

        <p className="muted small center">
          Your access token is stored only on the backend and never sent to the browser.
        </p>
      </form>
    </div>
  );
}
