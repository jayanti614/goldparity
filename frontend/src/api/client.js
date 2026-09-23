// Locally, this stays "/api" and Vite's dev-server proxy (vite.config.js)
// forwards it to the backend -- no env var needed for local dev.
//
// Once deployed, there's no dev-server proxy anymore (this becomes a
// static build), so VITE_API_BASE_URL must be set at build time to the
// real backend URL, e.g. https://goldparity-api.onrender.com/api
// (set this in Vercel's Environment Variables before deploying).
const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || `Request to ${path} failed (${res.status})`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  status: () => get("/status"),
  contracts: () => get("/contracts"),
  latestSignals: () => get("/signals/latest"),
  signalHistory: (symbol) => get(`/signals/history/${symbol}`),
  flaggedSignals: () => get("/signals/flagged"),
  backtest: () => get("/backtest"),
  carryHistory: () => get("/carry/history"),
};
