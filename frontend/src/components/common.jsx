export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export function RiskBar({ score }) {
  if (score === null || score === undefined) {
    return <span style={{ color: "var(--text)", fontSize: 13 }}>—</span>;
  }
  const pct = Math.round(score * 100);
  const color = score >= 0.75 ? "#d32f2f" : score >= 0.4 ? "#b8790a" : "#2ea043";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div className="risk-bar-track">
        <div className="risk-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 600, color }}>{pct}%</span>
    </div>
  );
}

export function formatArchetype(value) {
  if (!value) return "—";
  return value
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}
