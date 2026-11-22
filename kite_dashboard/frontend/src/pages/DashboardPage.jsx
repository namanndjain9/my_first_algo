import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { tabs } from "../tabs/index.js";

export default function DashboardPage({ userName, onLogout }) {
  const navigate = useNavigate();
  const [activeTabId, setActiveTabId] = useState(tabs[0].id);
  const [visitedTabIds, setVisitedTabIds] = useState([tabs[0].id]);
  const activeTab = tabs.find((t) => t.id === activeTabId) || tabs[0];

  function selectTab(id) {
    setActiveTabId(id);
    setVisitedTabIds((ids) => (ids.includes(id) ? ids : [...ids, id]));
  }

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      /* even if the backend call fails, return to login */
    }
    onLogout();
    navigate("/login", { replace: true });
  }

  // Called by tabs when the backend says the session has expired (HTTP 401).
  function handleSessionExpired() {
    onLogout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="dashboard">
      <header className="topbar">
        <div className="topbar-brand">
          <div className="brand-mark small">K</div>
          <span>Kite Dashboard</span>
        </div>
        <div className="topbar-right">
          {userName && <span className="muted">{userName}</span>}
          <button className="btn btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <nav className="tabs" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={tab.id === activeTabId}
            className={`tab ${tab.id === activeTabId ? "active" : ""}`}
            onClick={() => selectTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="tab-content">
        {/* Tabs stay mounted after their first visit, so results survive switching tabs */}
        {tabs
          .filter((tab) => visitedTabIds.includes(tab.id))
          .map(({ id, component: TabComponent }) => (
            <div key={id} hidden={id !== activeTab.id}>
              <TabComponent onSessionExpired={handleSessionExpired} />
            </div>
          ))}
      </main>
    </div>
  );
}
