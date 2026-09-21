import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { StatusBadge, RiskBar, formatArchetype } from "../components/common";

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

export default function TransactionDetailPage() {
  const { id } = useParams();
  const [transaction, setTransaction] = useState(null);
  const [flag, setFlag] = useState(null);
  const [decisionLog, setDecisionLog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([api.getTransaction(id), api.getTransactionFlag(id), api.getDecisionLog(id)])
      .then(([tx, flagData, log]) => {
        setTransaction(tx);
        setFlag(flagData);
        setDecisionLog(log);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="empty-state">Loading transaction…</div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!transaction) return null;

  const reasonCodes = flag?.reason_codes || {};
  const finalExplanation = resolveFinalExplanation(decisionLog, transaction);

  return (
    <div>
      <Link to="/queue" className="link-back">&larr; Back to risk queue</Link>
      <div className="page-header">
        <div>
          <h1>Transaction {transaction.id.slice(0, 8)}</h1>
          <p>{transaction.event_type.replace("_", " ")} · ${transaction.amount.toLocaleString()}</p>
        </div>
        <StatusBadge status={transaction.status} />
      </div>

      <div className="card">
        <h2>Raw transaction</h2>
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
          <h2>Risk assessment</h2>
          <div className="score-row">
            <div className="score-item">
              <label>Fused risk score</label>
              <div className="value"><RiskBar score={flag.risk_score} /></div>
            </div>
            <div className="score-item">
              <label>Supervised score</label>
              <div className="value" style={{ fontSize: 18 }}>{(flag.supervised_score ?? 0).toFixed(3)}</div>
            </div>
            <div className="score-item">
              <label>Anomaly score</label>
              <div className="value" style={{ fontSize: 18 }}>{(flag.anomaly_score ?? 0).toFixed(3)}</div>
            </div>
            <div className="score-item">
              <label>Decision</label>
              <div className="value"><StatusBadge status={transaction.status} /></div>
            </div>
          </div>
          <div className="kv-grid" style={{ marginTop: 12 }}>
            <div className="kv"><label>Archetype</label><span>{formatArchetype(reasonCodes.archetype)}</span></div>
          </div>
          {reasonCodes.top_features && (
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 11.5, textTransform: "uppercase", color: "var(--text)" }}>
                Top contributing features
              </label>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontSize: 13.5 }}>
                {reasonCodes.top_features.map((f, i) => (
                  <li key={i}>{typeof f === "string" ? f : JSON.stringify(f)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      ) : (
        <div className="card">
          <h2>Risk assessment</h2>
          <p style={{ fontSize: 14, color: "var(--text)" }}>
            This transaction has not been evaluated by the agent pipeline yet.
          </p>
        </div>
      )}

      {finalExplanation && (
        <div className="card">
          <h2>Agent explanation</h2>
          <div className="explanation-box">{finalExplanation.text}</div>
          <span className="provider-tag">explained by {finalExplanation.provider}</span>
        </div>
      )}

      {decisionLog && (
        <div className="card">
          <h2>Full audit trail</h2>
          <div className="audit-trail">
            {decisionLog.map((row) => (
              <div className="audit-step" key={row.id}>
                <div className="step-name">{row.node_name}</div>
                <div className="step-time">{new Date(row.created_at).toLocaleString()}</div>
                <pre>{JSON.stringify(row.output_snapshot, null, 2)}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
