import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { api } from "../lib/api";
import { formatArchetype } from "../components/common";

const DECISION_COLORS = { allow: "#2ea043", escalate: "#b8790a", block: "#d32f2f" };
const ARCHETYPE_COLORS = ["#aa3bff", "#2ea043", "#b8790a", "#d32f2f", "#4b8bf5"];

export default function AnalyticsPage() {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getAnalyticsFraudFlags(1000)
      .then(setFlags)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => {
    const total = flags.length;
    const decisionCounts = { allow: 0, escalate: 0, block: 0 };
    const archetypeCounts = {};
    const eventTypeRisk = {};
    const histogramBuckets = Array.from({ length: 10 }, (_, i) => ({
      bucket: `${i * 10}-${i * 10 + 10}%`,
      count: 0,
    }));

    for (const flag of flags) {
      decisionCounts[flag.decision] = (decisionCounts[flag.decision] || 0) + 1;
      const archetype = flag.archetype || "unclassified";
      archetypeCounts[archetype] = (archetypeCounts[archetype] || 0) + 1;

      const et = flag.event_type || "unknown";
      if (!eventTypeRisk[et]) eventTypeRisk[et] = { sum: 0, count: 0 };
      eventTypeRisk[et].sum += flag.risk_score;
      eventTypeRisk[et].count += 1;

      const bucketIndex = Math.min(9, Math.floor(flag.risk_score * 10));
      histogramBuckets[bucketIndex].count += 1;
    }

    const avgRisk = total ? flags.reduce((sum, f) => sum + f.risk_score, 0) / total : 0;

    return {
      total,
      decisionCounts,
      avgRisk,
      decisionData: Object.entries(decisionCounts).map(([decision, count]) => ({ decision, count })),
      archetypeData: Object.entries(archetypeCounts).map(([archetype, count]) => ({
        name: formatArchetype(archetype),
        value: count,
      })),
      eventTypeData: Object.entries(eventTypeRisk).map(([eventType, { sum, count }]) => ({
        eventType: eventType.replace("_", " "),
        avgRisk: Number(((sum / count) * 100).toFixed(1)),
      })),
      histogramBuckets,
    };
  }, [flags]);

  if (loading) return <div className="empty-state">Loading analytics…</div>;
  if (error) return <div className="error-banner">{error}</div>;

  if (stats.total === 0) {
    return (
      <div>
        <div className="page-header">
          <div>
            <h1>Analytics</h1>
            <p>Aggregate view of every decision the fraud agent has made.</p>
          </div>
        </div>
        <div className="empty-state">No decided transactions yet. Run the pipeline to see analytics.</div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Analytics</h1>
          <p>Aggregate view of every decision the fraud agent has made.</p>
        </div>
      </div>

      <div className="stat-row">
        <div className="stat-card">
          <label>Total decisions</label>
          <div className="value">{stats.total}</div>
        </div>
        <div className="stat-card">
          <label>Blocked</label>
          <div className="value">{stats.decisionCounts.block || 0}</div>
        </div>
        <div className="stat-card">
          <label>Escalated</label>
          <div className="value">{stats.decisionCounts.escalate || 0}</div>
        </div>
        <div className="stat-card">
          <label>Avg risk score</label>
          <div className="value">{Math.round(stats.avgRisk * 100)}%</div>
        </div>
      </div>

      <div className="chart-grid">
        <div className="card">
          <h2>Decisions</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.decisionData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="decision" stroke="var(--text)" fontSize={12} />
              <YAxis stroke="var(--text)" fontSize={12} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count">
                {stats.decisionData.map((entry) => (
                  <Cell key={entry.decision} fill={DECISION_COLORS[entry.decision] || "#999"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2>Fraud archetypes</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={stats.archetypeData} dataKey="value" nameKey="name" outerRadius={90} label>
                {stats.archetypeData.map((_, i) => (
                  <Cell key={i} fill={ARCHETYPE_COLORS[i % ARCHETYPE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2>Avg risk by event type</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.eventTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="eventType" stroke="var(--text)" fontSize={11} />
              <YAxis stroke="var(--text)" fontSize={12} unit="%" />
              <Tooltip />
              <Bar dataKey="avgRisk" fill="#aa3bff" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2>Risk score distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.histogramBuckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="bucket" stroke="var(--text)" fontSize={10} />
              <YAxis stroke="var(--text)" fontSize={12} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#4b8bf5" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
