import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Check,
  CheckCircle2,
  Copy,
  FileJson,
  Fingerprint,
  ListTree,
  MessageSquareText,
  ShieldQuestion,
  ShieldX,
  Users,
  Sparkles,
} from "lucide-react";
import { api } from "../lib/api";
import { useToast } from "../lib/toast";
import { AuditStep, StatusBadge, RiskGauge, SmartLoading, formatArchetype } from "../components/common";

function buildFallbackExplanation(detectOutput, transaction) {
  const topFeature = detectOutput.top_features?.[0];
  const featureClause = topFeature
    ? ` The strongest contributing factor was ${topFeature.feature}.`
    : "";
  return (
    `This ${transaction.event_type.replace("_", " ")} of ${transaction.amount.toFixed(2)} received a ` +
    `fused risk score of ${detectOutput.risk_score.toFixed(2)}, matching the pattern ` +
    `'${detectOutput.label}': ${detectOutput.rationale}${featureClause}`
  );
}

function resolveFinalExplanation(decisionLog, transaction) {
  if (!decisionLog) return null;
  const guardrailSteps = decisionLog.filter((row) => row.node_name === "guardrail");
  const explainSteps = decisionLog.filter((row) => row.node_name === "explain");
  const detectStep = decisionLog.find((row) => row.node_name === "detect");
  const lastGuardrail = guardrailSteps[guardrailSteps.length - 1];

  if (!lastGuardrail) return null;

  if (lastGuardrail.output_snapshot?.action === "fallback_to_template" && detectStep) {
    return { text: buildFallbackExplanation(detectStep.output_snapshot, transaction), provider: "template_fallback" };
  }

  const lastExplain = explainSteps[explainSteps.length - 1];
  if (!lastExplain) return null;
  return { text: lastExplain.output_snapshot?.explanation, provider: lastExplain.output_snapshot?.provider };
}

function CopyButton({ value }) {
  const toast = useToast();
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast?.push("Copied to clipboard", "success");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast?.push("Could not copy", "error");
    }
  }

  return (
    <button className="copy-btn" onClick={copy} type="button">
      {copied ? <Check /> : <Copy />}
      {copied ? "Copied" : "Copy ID"}
    </button>
  );
}

export default function TransactionDetailPage() {
  const { id } = useParams();
  const toast = useToast();
  const [transaction, setTransaction] = useState(null);
  const [flag, setFlag] = useState(null);
  const [decisionLog, setDecisionLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedbackHistory, setFeedbackHistory] = useState([]);
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([api.getTransaction(id), api.getTransactionFlag(id), api.getDecisionLog(id), api.getFeedback(id)])
      .then(([tx, flagData, log, feedback]) => {
        setTransaction(tx);
        setFlag(flagData);
        setDecisionLog(log);
        setFeedbackHistory(feedback || []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function submitFeedback(decision) {
    setSubmittingFeedback(true);
    try {
      const entry = await api.submitFeedback(id, { decision, notes: feedbackNotes || null });
      setFeedbackHistory((prev) => [entry, ...prev]);
      setFeedbackNotes("");
      toast?.push(
        decision === "block" ? "Marked as confirmed fraud" : "Marked as false positive",
        "success"
      );
    } catch {
      toast?.push("Could not save feedback", "error");
    } finally {
      setSubmittingFeedback(false);
    }
  }

  if (loading) return <SmartLoading label="Loading transaction…" />;
  if (error) return <div className="error-banner">{error}</div>;
  if (!transaction) return null;

  const reasonCodes = flag?.reason_codes || {};
  const finalExplanation = resolveFinalExplanation(decisionLog, transaction);

  return (
    <div>
      <Link to="/queue" className="link-back"><ArrowLeft />Back to risk queue</Link>
      <div className="page-header">
        <div>
          <h1>Transaction {transaction.id.slice(0, 8)}</h1>
          <p>{transaction.event_type.replace("_", " ")} · ${transaction.amount.toLocaleString()}</p>
          <div className="txn-id-row" style={{ marginTop: 6 }}>
            <Fingerprint size={13} />
            {transaction.id}
            <CopyButton value={transaction.id} />
          </div>
        </div>
        <StatusBadge status={transaction.status} />
      </div>

      <div className="card">
        <h2><FileJson />Raw transaction</h2>
        <div className="kv-grid">
          <div className="kv"><label>Origin account</label><span>{transaction.origin_account}</span></div>
          <div className="kv"><label>Dest account</label><span>{transaction.dest_account || "—"}</span></div>
          <div className="kv"><label>Origin balance before</label><span>{transaction.origin_balance_before ?? "—"}</span></div>
          <div className="kv"><label>Origin balance after</label><span>{transaction.origin_balance_after ?? "—"}</span></div>
          <div className="kv"><label>Dest balance before</label><span>{transaction.dest_balance_before ?? "—"}</span></div>
          <div className="kv"><label>Dest balance after</label><span>{transaction.dest_balance_after ?? "—"}</span></div>
          <div className="kv"><label>Created</label><span>{new Date(transaction.created_at).toLocaleString()}</span></div>
          {transaction.is_fraud_label !== null && (
            <div className="kv"><label>Ground-truth label</label><span>{transaction.is_fraud_label ? "Fraud" : "Legitimate"}</span></div>
          )}
        </div>
      </div>

      {flag ? (
        <div className="card">
          <h2><ShieldQuestion />Risk assessment</h2>
          <div className="hero-risk-row">
            <RiskGauge score={flag.risk_score} />
            <div className="hero-risk-meta">
              <div className="hero-risk-meta-row">
                <div className="score-item">
                  <label>Supervised score</label>
                  <div className="value">{(flag.supervised_score ?? 0).toFixed(3)}</div>
                </div>
                <div className="score-item">
                  <label>Anomaly score</label>
                  <div className="value">{(flag.anomaly_score ?? 0).toFixed(3)}</div>
                </div>
                <div className="score-item">
                  <label>Decision</label>
                  <div className="value"><StatusBadge status={transaction.status} /></div>
                </div>
              </div>
              <div className="kv">
                <label>Archetype</label>
                <span style={{ fontFamily: "var(--sans)", fontSize: 15 }}>{formatArchetype(reasonCodes.archetype)}</span>
              </div>
            </div>
          </div>
          {reasonCodes.top_features && (
            <div>
              <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.04em", color: "var(--text-dim)" }}>
                Top contributing features
              </label>
              <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: 13.5, color: "var(--text-h)", lineHeight: 1.8 }}>
                {reasonCodes.top_features.map((f, i) => (
                  <li key={i}>{typeof f === "string" ? f : JSON.stringify(f)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <h2><ShieldQuestion />Risk assessment</h2>
          <p style={{ fontSize: 14, color: "var(--text)" }}>
            This transaction has not been evaluated by the agent pipeline yet.
          </p>
        </div>
      )}

      <div className="card">
        <h2><Users />Analyst review</h2>
        <p style={{ fontSize: 13, color: "var(--text-dim)", marginBottom: 12 }}>
          Confirm the model's call so future scoring can learn from analyst outcomes.
        </p>
        <textarea
          className="feedback-notes"
          placeholder="Optional notes for this review…"
          value={feedbackNotes}
          onChange={(e) => setFeedbackNotes(e.target.value)}
          rows={2}
        />
        <div style={{ display: "flex", gap: 10, marginTop: 10 }}>
          <button className="btn" disabled={submittingFeedback} onClick={() => submitFeedback("block")}>
            <ShieldX />
            Confirm as fraud
          </button>
          <button
            className="btn btn-secondary"
            disabled={submittingFeedback}
            onClick={() => submitFeedback("approve")}
          >
            <CheckCircle2 />
            Mark as false positive
          </button>
        </div>
        {feedbackHistory.length > 0 && (
          <div className="feedback-history">
            {feedbackHistory.map((entry) => (
              <div className="feedback-entry" key={entry.id}>
                <span className={`badge ${entry.decision === "block" ? "badge-blocked" : "badge-allowed"}`}>
                  {entry.decision === "block" ? "Confirmed fraud" : "False positive"}
                </span>
                <span className="feedback-meta">
                  {entry.analyst_email || "analyst"} · {new Date(entry.created_at).toLocaleString()}
                </span>
                {entry.notes && <p className="feedback-note-text">{entry.notes}</p>}
              </div>
            ))}
          </div>
        )}
      </div>

      {finalExplanation && (
        <div className="card">
          <h2><MessageSquareText />Agent explanation</h2>
          <div className="explanation-box">{finalExplanation.text}</div>
          <span className="provider-tag"><Sparkles />explained by {finalExplanation.provider}</span>
        </div>
      )}

      {decisionLog && (
        <div className="card">
          <h2><ListTree />Full audit trail</h2>
          <div className="audit-trail">
            {decisionLog.map((row, i) => (
              <AuditStep key={row.id} row={row} defaultOpen={i === decisionLog.length - 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
