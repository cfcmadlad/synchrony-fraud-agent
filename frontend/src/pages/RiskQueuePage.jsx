import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { StatusBadge, RiskBar, formatArchetype } from "../components/common";

const STATUS_TABS = [
  { value: "escalated", label: "Escalated" },
  { value: "blocked", label: "Blocked" },
  { value: "allowed", label: "Allowed" },
  { value: "", label: "All" },
  { value: "pending", label: "Not yet evaluated" },
];

const PAGE_SIZE = 25;

const SIMULATE_DEFAULTS = {
  event_type: "loan_disbursement",
  step: 5,
  amount: 9500,
  origin_account: "DEMO_ORIGIN_001",
  dest_account: "DEMO_MERCHANT_001",
  origin_balance_before: 9500,
  origin_balance_after: 0,
  dest_balance_before: 500,
  dest_balance_after: 10000,
};

export default function RiskQueuePage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("escalated");
  const [page, setPage] = useState(0);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showSimulate, setShowSimulate] = useState(false);
  const [form, setForm] = useState(SIMULATE_DEFAULTS);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simError, setSimError] = useState(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTransactions({ status, limit: PAGE_SIZE, offset: page * PAGE_SIZE });
      setTransactions(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [status, page]);

  function selectStatus(value) {
    setStatus(value);
    setPage(0);
  }

  async function handleSimulate(e) {
    e.preventDefault();
    setSimulating(true);
    setSimError(null);
    setSimResult(null);
    try {
      const payload = {
        ...form,
        step: Number(form.step),
        amount: Number(form.amount),
        origin_balance_before: Number(form.origin_balance_before),
        origin_balance_after: Number(form.origin_balance_after),
        dest_balance_before: Number(form.dest_balance_before),
        dest_balance_after: Number(form.dest_balance_after),
      };
      const result = await api.runPipeline(payload);
      setSimResult(result);
      load();
    } catch (err) {
      setSimError(err.message);
    } finally {
      setSimulating(false);
    }
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Risk Queue</h1>
          <p>Transactions scored and decided by the fraud agent pipeline.</p>
        </div>
        <button className="btn" onClick={() => setShowSimulate((v) => !v)}>
          {showSimulate ? "Close" : "Simulate transaction"}
        </button>
      </div>

      {showSimulate && (
        <div className="card">
          <h2>Run a transaction through the live agent pipeline</h2>
          <form className="simulate-form" onSubmit={handleSimulate}>
            <div className="field">
              <label>Event type</label>
              <select value={form.event_type} onChange={(e) => updateField("event_type", e.target.value)}>
                <option value="loan_disbursement">Loan disbursement</option>
                <option value="installment_repayment">Installment repayment</option>
                <option value="fee_charge">Fee charge</option>
                <option value="account_funding">Account funding</option>
              </select>
            </div>
            <div className="field">
              <label>Amount</label>
              <input type="number" value={form.amount} onChange={(e) => updateField("amount", e.target.value)} />
            </div>
            <div className="field">
              <label>Step (simulation hour)</label>
              <input type="number" value={form.step} onChange={(e) => updateField("step", e.target.value)} />
            </div>
            <div className="field">
              <label>Origin account</label>
              <input value={form.origin_account} onChange={(e) => updateField("origin_account", e.target.value)} />
            </div>
            <div className="field">
              <label>Dest account</label>
              <input value={form.dest_account} onChange={(e) => updateField("dest_account", e.target.value)} />
            </div>
            <div className="field">
              <label>Origin balance before</label>
              <input
                type="number"
                value={form.origin_balance_before}
                onChange={(e) => updateField("origin_balance_before", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Origin balance after</label>
              <input
                type="number"
                value={form.origin_balance_after}
                onChange={(e) => updateField("origin_balance_after", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Dest balance before</label>
              <input
                type="number"
                value={form.dest_balance_before}
                onChange={(e) => updateField("dest_balance_before", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Dest balance after</label>
              <input
                type="number"
                value={form.dest_balance_after}
                onChange={(e) => updateField("dest_balance_after", e.target.value)}
              />
            </div>
            <button className="btn" type="submit" disabled={simulating}>
              {simulating ? "Running pipeline…" : "Run pipeline"}
            </button>
          </form>

          {simError && <div className="error-banner" style={{ marginTop: 14 }}>{simError}</div>}

          {simResult && (
            <div className="simulate-result">
              <div className="score-row">
                <div className="score-item">
                  <label>Risk score</label>
                  <div className="value">{Math.round(simResult.risk_score * 100)}%</div>
                </div>
                <div className="score-item">
                  <label>Decision</label>
                  <div className="value"><StatusBadge status={simResult.decision === "allow" ? "allowed" : simResult.decision === "block" ? "blocked" : "escalated"} /></div>
                </div>
                <div className="score-item">
                  <label>Archetype</label>
                  <div className="value" style={{ fontSize: 15 }}>{formatArchetype(simResult.archetype)}</div>
                </div>
              </div>
              <div className="explanation-box">{simResult.explanation}</div>
              <span className="provider-tag">explained by {simResult.explanation_provider}</span>
              <button
                className="btn btn-secondary"
                style={{ marginTop: 12 }}
                onClick={() => navigate(`/transactions/${simResult.transaction_id}`)}
              >
                View full case
              </button>
            </div>
          )}
        </div>
      )}

      <div className="filter-bar">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            className={status === tab.value ? "active" : ""}
            onClick={() => selectStatus(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}

      <table className="data-table">
        <thead>
          <tr>
            <th>Event type</th>
            <th>Amount</th>
            <th>Origin account</th>
            <th>Risk</th>
            <th>Status</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <tr key={tx.id} onClick={() => navigate(`/transactions/${tx.id}`)}>
              <td>{tx.event_type.replace("_", " ")}</td>
              <td>${tx.amount.toLocaleString()}</td>
              <td>{tx.origin_account}</td>
              <td><RiskBar score={tx.risk_score} /></td>
              <td><StatusBadge status={tx.status} /></td>
              <td>{new Date(tx.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {!loading && transactions.length === 0 && (
        <div className="empty-state">No transactions match this filter.</div>
      )}

      <div className="pagination-bar">
        <button disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
          Previous
        </button>
        <button disabled={transactions.length < PAGE_SIZE} onClick={() => setPage((p) => p + 1)}>
          Next
        </button>
      </div>
    </div>
  );
}
