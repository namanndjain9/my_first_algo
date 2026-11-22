import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api.js";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";

export default function App() {
  // null = still checking with the backend
  const [session, setSession] = useState(null);

  // On first load, ask the backend if a saved access token is still valid.
  useEffect(() => {
    api
      .getStatus()
      .then((status) => setSession(status))
      .catch(() => setSession({ logged_in: false }));
  }, []);

  if (session === null) {
    return <div className="center-screen muted">Checking session…</div>;
  }

  const handleLogin = (status) => setSession(status);
  const handleLogout = () => setSession({ logged_in: false });

  return (
    <Routes>
      <Route
        path="/login"
        element={
          session.logged_in ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <LoginPage onLogin={handleLogin} notice={session.message} />
          )
        }
      />
      <Route
        path="/dashboard"
        element={
          session.logged_in ? (
            <DashboardPage userName={session.user_name} onLogout={handleLogout} />
          ) : (
            <Navigate to={`/login${window.location.search}`} replace />
          )
        }
      />
      <Route path="*" element={<Navigate to={`/dashboard${window.location.search}`} replace />} />
    </Routes>
  );
}
