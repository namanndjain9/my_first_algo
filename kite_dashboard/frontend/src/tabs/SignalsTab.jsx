import { useState } from "react";
import { api } from "../api.js";

const DEFAULTS = { short_sma: 6, long_sma: 30, lookback_days: 365, max_stocks: 100 };

// Each input: which setting it controls, its label, a short hint, and allowed range.
const FIELDS = [
  { key: "short_sma", label: "Short SMA", hint: "Fast average (days)", min: 1, max: 200 },
  { key: "long_sma", label: "Long SMA", hint: "Slow average (days)", min: 2, max: 400 },
  { key: "lookback_days", label: "Lookback Days", hint: "Calendar days of history", min: 30, max: 2000 },
  { key: "max_stocks", label: "Max Stocks", hint: "1 – 100 Nifty 100 stocks", min: 1, max: 100 },
];

const FILTERS = ["All", "Bullish", "Bearish"];

const formatPrice = (n) =>
  n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const formatDate = (iso) =>
  new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

export default function SignalsTab({ onSessionExpired }) {
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("All");

  const updateField = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  async function handleGenerate(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const params = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, Number(v)])
      );
      setResult(await api.getSignals(params));
      setFilter("All");
    } catch (err) {
      if (err.status === 401) return onSessionExpired();
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Kite allows ~3 history requests/second, so each stock takes about 0.35s.
  const estimatedSeconds = Math.ceil(Number(form.max_stocks || 0) * 0.4) + 3;

  const signals = result?.signals || [];
  const visible = filter === "All" ? signals : signals.filter((s) => s.type === filter);
  const bullishCount = signals.filter((s) => s.type === "Bullish").length;
  const shortLabel = `SMA ${result?.params.short_sma ?? form.short_sma}`;
  const longLabel = `SMA ${result?.params.long_sma ?? form.long_sma}`;

  return (
    <section>
      <div className="section-header">
        <div>
          <h2>Nifty 100 SMA Crossover Signals</h2>
          <p className="muted small section-subtitle">
            Bullish = short SMA crosses above the long SMA. Bearish = it crosses below.
            Newest crossovers are ranked first.
          </p>
        </div>
      </div>

      <form className="card scan-form" onSubmit={handleGenerate}>
        <div className="form-grid">
          {FIELDS.map((field) => (
            <label className="field" key={field.key}>
              <span>{field.label}</span>
              <input
                type="number"
                min={field.min}
                max={field.max}
                value={form[field.key]}
                onChange={(e) => updateField(field.key, e.target.value)}
                disabled={loading}
                required
              />
              <small className="muted">{field.hint}</small>
            </label>
          ))}
        </div>
        <div className="form-actions">
          <button className="btn btn-ghost" type="button" onClick={() => setForm(DEFAULTS)} disabled={loading}>
            Reset
          </button>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Scanning…" : "Generate Signals"}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {loading && (
        <div className="card loading-card">
          <div className="spinner" />
          <div>
            <div>Scanning {form.max_stocks} stocks…</div>
            <div className="muted small">This takes about {estimatedSeconds} seconds (Kite rate limits).</div>
          </div>
        </div>
      )}

      {!loading && result && (
        <>
          <div className="grid stats">
            <Stat label="Stocks scanned" value={result.scanned} />
            <Stat label="Signals found" value={signals.length} />
            <Stat label="Bullish" value={bullishCount} tone="success" />
            <Stat label="Bearish" value={signals.length - bullishCount} tone="danger" />
          </div>

          <div className="card table-card">
            <div className="table-toolbar">
              <div className="segmented">
                {FILTERS.map((f) => (
                  <button
                    key={f}
                    type="button"
                    className={filter === f ? "active" : ""}
                    onClick={() => setFilter(f)}
                  >
                    {f}
                  </button>
                ))}
              </div>
              {(result.no_crossover.length > 0 || result.skipped.length > 0) && (
                <span className="muted small">
                  {result.no_crossover.length} with no crossover in range
                  {result.skipped.length > 0 && (
                    <span title={result.skipped.map((s) => `${s.ticker}: ${s.reason}`).join("\n")}>
                      {" "}· {result.skipped.length} skipped ⓘ
                    </span>
                  )}
                </span>
              )}
            </div>

            {visible.length === 0 ? (
              <div className="empty muted">No signals match this filter.</div>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th className="num">Rank</th>
                      <th>Ticker</th>
                      <th>Company</th>
                      <th>Crossover Type</th>
                      <th>Crossover Date</th>
                      <th className="num">Close</th>
                      <th className="num">{shortLabel}</th>
                      <th className="num">{longLabel}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((s) => (
                      <tr key={s.ticker}>
                        <td className="num muted">{s.rank}</td>
                        <td className="ticker">{s.ticker}</td>
                        <td className="company">{s.company}</td>
                        <td>
                          <span className={`badge ${s.type === "Bullish" ? "badge-success" : "badge-danger"}`}>
                            {s.type === "Bullish" ? "▲" : "▼"} {s.type}
                          </span>
                        </td>
                        <td>{formatDate(s.date)}</td>
                        <td className="num">{formatPrice(s.close)}</td>
                        <td className="num">{formatPrice(s.sma_short)}</td>
                        <td className="num">{formatPrice(s.sma_long)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {!loading && !result && !error && (
        <div className="card empty muted">
          Set your parameters and click <strong>Generate Signals</strong> to scan the Nifty 100.
        </div>
      )}
    </section>
  );
}

function Stat({ label, value, tone }) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className={`card-value ${tone ? `text-${tone}` : ""}`}>{value}</div>
    </div>
  );
}
