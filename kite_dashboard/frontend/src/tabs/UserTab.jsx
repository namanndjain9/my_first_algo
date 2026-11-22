import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function UserTab({ onSessionExpired }) {
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadProfile() {
    setLoading(true);
    setError("");
    try {
      setProfile(await api.getProfile());
    } catch (err) {
      if (err.status === 401) return onSessionExpired();
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadProfile();
  }, []);

  if (loading) return <div className="muted">Loading profile…</div>;

  if (error) {
    return (
      <div className="alert alert-error">
        {error}
        <button className="btn btn-ghost" onClick={loadProfile}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <section>
      <div className="section-header">
        <h2>User Profile</h2>
        <button className="btn btn-ghost" onClick={loadProfile}>
          Refresh
        </button>
      </div>

      <div className="grid">
        <InfoCard label="User Name" value={profile.user_name} />
        <InfoCard label="User ID" value={profile.user_id} />
      </div>

      <div className="grid">
        <ListCard label="Products" items={profile.products} />
        <ListCard label="Exchanges" items={profile.exchanges} />
      </div>
    </section>
  );
}

function InfoCard({ label, value }) {
  return (
    <div className="card">
      <div className="card-label">{label}</div>
      <div className="card-value">{value || "—"}</div>
    </div>
  );
}

function ListCard({ label, items = [] }) {
  return (
    <div className="card">
      <div className="card-label">
        {label} <span className="count">{items.length}</span>
      </div>
      <div className="chips">
        {items.length ? items.map((item) => <span className="chip" key={item}>{item}</span>) : "—"}
      </div>
    </div>
  );
}
