const BASE = "/api";

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
