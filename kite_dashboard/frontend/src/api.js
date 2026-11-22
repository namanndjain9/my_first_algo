// All calls to the FastAPI backend live here.
// Vite forwards "/api/..." to http://127.0.0.1:8000 (see vite.config.js).

async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    // FastAPI sends errors as { detail: "..." } or { detail: [{ msg: "..." }] }
    let message = data.detail || `Request failed (${response.status})`;
    if (Array.isArray(message)) message = message.map((d) => d.msg.replace(/^Value error, /, "")).join(", ");
    if (response.status === 500 || response.status === 504) {
      message = "Backend is not reachable. Is the FastAPI server running on port 8000?";
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

export const api = {
  getStatus: () => request("/auth/status"),
  login: (credentials) =>
    request("/auth/login", { method: "POST", body: JSON.stringify(credentials) }),
  logout: () => request("/auth/logout", { method: "POST" }),
  getProfile: () => request("/profile"),
  getSignals: (params) =>
    request("/signals", { method: "POST", body: JSON.stringify(params) }),
};
