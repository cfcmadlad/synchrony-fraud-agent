import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function authHeader() {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(await authHeader()),
    ...options.headers,
  };
  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.text();
    const err = new Error(`${res.status} ${res.statusText}: ${body}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

function toQuery(params) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(entries).toString()}`;
}

export const api = {
  health: () => request("/api/health"),
  getMe: () => request("/api/me"),
  listTransactions: ({ status, limit = 50, offset = 0, orderBy = "risk_score" } = {}) =>
    request(`/api/transactions${toQuery({ status, limit, offset, order_by: orderBy })}`),
  getTransaction: (id) => request(`/api/transactions/${id}`),
  getTransactionFlag: (id) => request(`/api/transactions/${id}/flag`).catch((err) => {
    if (err.status === 404) return null;
    throw err;
  }),
  getDecisionLog: (id) => request(`/api/decision-log/${id}`).catch((err) => {
    if (err.status === 403 || err.status === 404) return null;
    throw err;
  }),
  getAnalyticsFraudFlags: (limit = 1000) => request(`/api/analytics/fraud-flags${toQuery({ limit })}`),
  runPipeline: (payload) => request("/api/pipeline/run", { method: "POST", body: JSON.stringify(payload) }),
};
