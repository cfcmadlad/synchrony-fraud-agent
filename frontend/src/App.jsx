import { useState } from "react";
import { api } from "./lib/api";
import "./App.css";

function App() {
  const [health, setHealth] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function checkHealth() {
    setError(null);
    try {
      setHealth(await api.health());
    } catch (err) {
      setError(err.message);
    }
  }

  async function sendDummyTransaction() {
    setError(null);
    setLoading(true);
    try {
      await api.createDummyTransaction();
      setTransactions(await api.listTransactions());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <h1>Synchrony Fraud Agent — Stage 1 wiring check</h1>
      <p className="subtitle">
        This screen only proves the plumbing works: React → FastAPI → Supabase → FastAPI → React.
        Real risk scoring, the agent pipeline, and the analyst UI come in later stages.
      </p>

      <div className="actions">
        <button onClick={checkHealth}>Check backend health</button>
        <button onClick={sendDummyTransaction} disabled={loading}>
          {loading ? "Sending…" : "Send dummy loan-disbursement event"}
        </button>
      </div>

      {health && (
        <pre className="panel">{JSON.stringify(health, null, 2)}</pre>
      )}

      {error && <p className="error">{error}</p>}

      {transactions.length > 0 && (
        <table className="panel">
          <thead>
            <tr>
              <th>Event type</th>
              <th>Amount</th>
              <th>Origin account</th>
              <th>Status</th>
              <th>Created at</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => (
              <tr key={tx.id}>
                <td>{tx.event_type}</td>
                <td>{tx.amount}</td>
                <td>{tx.origin_account}</td>
                <td>{tx.status}</td>
                <td>{new Date(tx.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default App;
