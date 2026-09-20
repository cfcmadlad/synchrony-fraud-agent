const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  createDummyTransaction: () => request("/api/transactions/dummy", { method: "POST" }),
  listTransactions: (limit = 50) => request(`/api/transactions?limit=${limit}`),
  getTransaction: (id) => request(`/api/transactions/${id}`),
};
