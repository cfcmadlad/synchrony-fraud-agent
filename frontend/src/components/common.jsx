import { useState } from "react";
import { Clock3, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";

const STATUS_ICON = {
  pending: Clock3,
  allowed: ShieldCheck,
  escalated: ShieldAlert,
  blocked: ShieldX,
};

export function StatusBadge({ status }) {
  const Icon = STATUS_ICON[status] || Clock3;
  return (
    <span className={`badge badge-${status}`}>
      <Icon />
      {status}
    </span>
  );
}

export function riskColor(score) {
  if (score === null || score === undefined) return "var(--text-dim)";
  if (score >= 0.75) return "var(--danger)";
  if (score >= 0.4) return "var(--warning)";
  return "var(--success)";
}

export function RiskBar({ score }) {
  if (score === null || score === undefined) {
    return <span style={{ color: "var(--text-dim)", fontSize: 12.5 }}>Not scored</span>;
  }
  const pct = Math.round(score * 100);
  const color = riskColor(score);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
      <div className="risk-bar-track">
        <div className="risk-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span style={{ fontSize: 12.5, fontWeight: 700, color, fontFamily: "var(--mono)", minWidth: 32 }}>{pct}%</span>
    </div>
  );
}

export function RiskGauge({ score, size = 110 }) {
  const pct = score === null || score === undefined ? 0 : score;
  const color = riskColor(score);
  const r = 58;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - pct);
  return (
    <div className="risk-gauge" style={{ width: size, height: size }}>
      <svg viewBox="0 0 140 140">
        <circle className="risk-gauge-track" cx="70" cy="70" r={r} />
        <circle
          className="risk-gauge-fill"
          cx="70"
          cy="70"
          r={r}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="risk-gauge-label">
        <span className="risk-gauge-value">{score === null || score === undefined ? "—" : `${Math.round(score * 100)}%`}</span>
        <span className="risk-gauge-caption">Risk score</span>
      </div>
    </div>
  );
}

export function Skeleton({ width = "100%", height = 14, style = {} }) {
  return <div className="skeleton skeleton-text" style={{ width, height, ...style }} />;
}

export function SkeletonRow({ columns = 6 }) {
  return (
    <tr className="skeleton-row">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i}>
          <Skeleton width={i === 0 ? "70%" : "50%"} />
        </td>
      ))}
    </tr>
  );
}

export function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="empty-state">
      {Icon && <Icon />}
      <div>
        <div style={{ color: "var(--text-h)", fontWeight: 600, marginBottom: 4 }}>{title}</div>
        {description && <div style={{ fontSize: 13 }}>{description}</div>}
      </div>
    </div>
  );
}

function ChevronIcon({ open }) {
  return (
    <svg className={`audit-step-chevron ${open ? "open" : ""}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

export function AuditStep({ row, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="audit-step">
      <div className="audit-step-dot" />
      <div className="audit-step-header" onClick={() => setOpen((o) => !o)}>
        <ChevronIcon open={open} />
        <span className="step-name">{row.node_name}</span>
        <span className="step-time">{new Date(row.created_at).toLocaleTimeString()}</span>
      </div>
      <div className={`audit-step-body ${open ? "open" : ""}`}>
        <pre>{JSON.stringify(row.output_snapshot, null, 2)}</pre>
      </div>
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
