import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowUpDown,
  ChevronDown,
  ChevronUp,
  Inbox,
  ListTree,
  Pin,
  Play,
  Search,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../lib/toast";
import { AuditStep, StatusBadge, RiskBar, formatArchetype, SkeletonRow, EmptyState } from "../components/common";
import PinnedTransactions from "../components/PinnedTransactions";

const PIPELINE_STEPS = ["Ingest", "Detect", "Retrieve similar cases", "Explain (LLM)", "Guardrail check", "Decide"];

const PIN_STORAGE_KEY = "synchrony-pinned-transactions";

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

const COLUMNS = [
  { key: "event_type", label: "Event type", sortable: false },
  { key: "amount", label: "Amount", sortable: true },
  { key: "origin_account", label: "Origin account", sortable: false },
  { key: "risk_score", label: "Risk", sortable: true },
  { key: "status", label: "Status", sortable: false },
  { key: "created_at", label: "Created", sortable: true },
  { key: "pin", label: "", sortable: false },
];

export default function RiskQueuePage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [status, setStatus] = useState("escalated");
  const [page, setPage] = useState(0);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState("risk_score");
  const [sortDir, setSortDir] = useState("desc");
  const [pinnedTransactions, setPinnedTransactions] = useState(() => {
    try {
      const raw = localStorage.getItem(PIN_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [showSimulate, setShowSimulate] = useState(false);
  const [form, setForm] = useState(SIMULATE_DEFAULTS);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState(null);
  const [simError, setSimError] = useState(null);
  const [simDecisionLog, setSimDecisionLog] = useState(null);
  const [simReasoningOpen, setSimReasoningOpen] = useState(false);

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

  useEffect(() => {
    try {
      localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify(pinnedTransactions));
    } catch {}
  }, [pinnedTransactions]);

  const pinnedIds = useMemo(() => new Set(pinnedTransactions.map((t) => t.id)), [pinnedTransactions]);

  function pinTransaction(tx) {
    setPinnedTransactions((prev) => (prev.some((t) => t.id === tx.id) ? prev : [...prev, tx]));
  }

  function unpinTransaction(id) {
    setPinnedTransactions((prev) => prev.filter((t) => t.id !== id));
  }

  function selectStatus(value) {
    setStatus(value);
    setPage(0);
  }

  function toggleSort(key) {
    if (sortKey === key) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const visibleRows = useMemo(() => {
    let rows = transactions.filter((tx) => !pinnedIds.has(tx.id));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter((tx) => tx.origin_account.toLowerCase().includes(q));
    }
    rows = [...rows].sort((a, b) => {
      let av = a[sortKey];
      let bv = b[sortKey];
      if (sortKey === "created_at") {
        av = new Date(av).getTime();
        bv = new Date(bv).getTime();
      }
      if (av === null || av === undefined) av = -Infinity;
      if (bv === null || bv === undefined) bv = -Infinity;
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [transactions, search, sortKey, sortDir, pinnedIds]);

  async function handleSimulate(e) {
    e.preventDefault();
    setSimulating(true);
    setSimError(null);
    setSimResult(null);
    setSimDecisionLog(null);
    setSimReasoningOpen(false);
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
      toast?.push(`Pipeline finished: ${result.decision} (${Math.round(result.risk_score * 100)}% risk)`, "success");
      load();
      api.getDecisionLog(result.transaction_id).then(setSimDecisionLog).catch(() => setSimDecisionLog(null));
    } catch (err) {
      setSimError(err.message);
      toast?.push("Pipeline run failed", "error");
    } finally {
      setSimulating(false);
    }
  }

  function updateField(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function sortIcon(key) {
    if (sortKey !== key) return <ArrowUpDown size={12} />;
    return sortDir === "asc" ? <ChevronUp size={12} /> : <ChevronDown size={12} />;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Risk Queue</h1>
          <p>Transactions scored and decided by the fraud agent pipeline.</p>
        </div>
        <button className="btn" onClick={() => setShowSimulate((v) => !v)}>
          {showSimulate ? <X /> : <Play />}
          {showSimulate ? "Close" : "Simulate transaction"}
        </button>
      </div>

      {showSimulate && (
        <div className="card">
          <h2><Sparkles />Run a transaction through the live agent pipeline</h2>
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
              {simulating && <span className="spinner" />}
              {simulating ? "Running pipeline…" : "Run pipeline"}
            </button>
          </form>

          {simulating && (
            <div className="sim-progress">
              <span className="spinner spinner-accent" />
              Running the live pipeline: {PIPELINE_STEPS.join(" → ")}. The explain step calls a real LLM, so
              this can take a few seconds.
            </div>
          )}

          {simError && (
            <div className="error-banner" style={{ marginTop: 14 }}>
              <AlertCircle />
              {simError}
            </div>
          )}

          {simResult && (
            <div className="simulate-result">
              <div className="simulate-result-header">
                <div className="score-item">
                  <label>Risk score</label>
                  <div className="value">{Math.round(simResult.risk_score * 100)}%</div>
                </div>
                <div className="score-item">
                  <label>Decision</label>
                  <div className="value">
                    <StatusBadge status={simResult.decision === "allow" ? "allowed" : simResult.decision === "block" ? "blocked" : "escalated"} />
                  </div>
                </div>
                <div className="score-item">
                  <label>Archetype</label>
                  <div className="value" style={{ fontSize: 15, fontFamily: "var(--sans)" }}>{formatArchetype(simResult.archetype)}</div>
                </div>
              </div>
              <div className="explanation-box">{simResult.explanation}</div>
              {simResult.explanation_provider === "template_fallback" ? (
                <span className="provider-tag provider-tag-fallback">
                  <ShieldAlert />
                  template fallback — the LLM call did not pass the guardrail or was unavailable, so this is a
                  generated-from-numbers summary, not model reasoning
                </span>
              ) : (
                <span className="provider-tag provider-tag-llm">
                  <Sparkles />
                  reasoned live by {simResult.explanation_provider}
                </span>
              )}

              <div className="sim-reasoning">
                <button
                  type="button"
                  className="sim-reasoning-toggle"
                  onClick={() => setSimReasoningOpen((v) => !v)}
                  disabled={!simDecisionLog}
                >
                  <ListTree size={14} />
                  {simDecisionLog ? "How the agent reasoned, step by step" : "Loading reasoning trace…"}
                  <ChevronDown size={13} className={`sim-reasoning-chevron ${simReasoningOpen ? "open" : ""}`} />
                </button>
                {simReasoningOpen && simDecisionLog && (
                  <div className="audit-trail" style={{ marginTop: 10 }}>
                    {simDecisionLog.map((row) => (
                      <AuditStep key={row.id} row={row} defaultOpen={row.node_name === "explain"} />
                    ))}
                  </div>
                )}
              </div>

              <button
                className="btn btn-secondary"
                style={{ marginTop: 14 }}
                onClick={() => navigate(`/transactions/${simResult.transaction_id}`)}
              >
                View full case
              </button>
            </div>
          )}
        </div>
      )}

      <PinnedTransactions
        transactions={pinnedTransactions}
        onUnpin={unpinTransaction}
        onOpen={(id) => navigate(`/transactions/${id}`)}
      />

      <div className="toolbar-row">
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
        <div className="input-icon-wrap search-input">
          <Search />
          <input
            placeholder="Search by account…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle />
          {error}
        </div>
      )}

      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`${col.sortable ? "sortable" : ""} ${sortKey === col.key ? "sort-active" : ""}`}
                  onClick={col.sortable ? () => toggleSort(col.key) : undefined}
                >
                  {col.label}
                  {col.sortable && <span className="sort-indicator">{sortIcon(col.key)}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading &&
              Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} columns={COLUMNS.length} />)}
            {!loading &&
              visibleRows.map((tx) => (
                <tr key={tx.id} className={`row-accent-${tx.status}`} onClick={() => navigate(`/transactions/${tx.id}`)}>
                  <td>{tx.event_type.replace("_", " ")}</td>
                  <td className="cell-amount">${tx.amount.toLocaleString()}</td>
                  <td className="cell-muted">{tx.origin_account}</td>
                  <td><RiskBar score={tx.risk_score} /></td>
                  <td><StatusBadge status={tx.status} /></td>
                  <td className="cell-muted">{new Date(tx.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="flex h-6 w-6 items-center justify-center rounded-full text-[var(--text-dim)] transition-colors hover:bg-[var(--bg-elevated-2)] hover:text-[var(--accent)]"
                      title="Pin for follow-up"
                      onClick={(e) => {
                        e.stopPropagation();
                        pinTransaction(tx);
                      }}
                      type="button"
                    >
                      <Pin size={13} />
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
        {!loading && visibleRows.length === 0 && (
          <EmptyState
            icon={Inbox}
            title="No transactions match"
            description={search ? "Try a different account search." : "Nothing in this filter yet."}
          />
        )}
      </div>

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
