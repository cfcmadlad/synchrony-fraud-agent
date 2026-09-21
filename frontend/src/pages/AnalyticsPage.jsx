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
import { Activity, AlertCircle, BarChart3, Gauge, PieChart as PieChartIcon, ShieldOff, ShieldQuestion, TrendingUp } from "lucide-react";
import { api } from "../lib/api";
import { formatArchetype } from "../components/common";

const DECISION_COLORS = { allow: "#16A34A", escalate: "#B45309", block: "#DC2626" };
const ARCHETYPE_COLORS = ["#0B63B0", "#16A34A", "#B45309", "#DC2626", "#7C4DBD"];
const AXIS_COLOR = "#8A93A3";
const GRID_COLOR = "#E2E7EF";

const tooltipStyle = {
  contentStyle: { background: "#FFFFFF", border: "1px solid #E2E7EF", borderRadius: 8, fontSize: 12.5, color: "#0B1220", boxShadow: "0 4px 16px rgba(15, 23, 42, 0.1)" },
  labelStyle: { color: "#5B6472" },
  itemStyle: { color: "#0B1220" },
};

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
    const topArchetypeEntry = Object.entries(archetypeCounts).sort((a, b) => b[1] - a[1])[0];

    return {
      total,
      decisionCounts,
      avgRisk,
      topArchetype: topArchetypeEntry ? { name: topArchetypeEntry[0], count: topArchetypeEntry[1] } : null,
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

  if (loading) return <div className="page-loading"><span className="spinner spinner-accent" />Loading analytics…</div>;
  if (error) return <div className="error-banner"><AlertCircle />{error}</div>;

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

  const blockRate = stats.total ? Math.round((stats.decisionCounts.block / stats.total) * 100) : 0;

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
          <span className="icon-badge icon-badge-blue"><BarChart3 /></span>
          <div className="stat-card-body">
            <label>Total decisions</label>
            <div className="value">{stats.total}</div>
          </div>
        </div>
        <div className="stat-card">
          <span className="icon-badge icon-badge-red"><ShieldOff /></span>
          <div className="stat-card-body">
            <label>Blocked</label>
            <div className="value">{stats.decisionCounts.block || 0}</div>
          </div>
        </div>
        <div className="stat-card">
          <span className="icon-badge icon-badge-amber"><ShieldQuestion /></span>
          <div className="stat-card-body">
            <label>Escalated</label>
            <div className="value">{stats.decisionCounts.escalate || 0}</div>
          </div>
        </div>
        <div className="stat-card">
          <span className="icon-badge icon-badge-purple"><Gauge /></span>
          <div className="stat-card-body">
            <label>Avg risk score</label>
            <div className="value">{Math.round(stats.avgRisk * 100)}%</div>
          </div>
        </div>
      </div>

      {stats.topArchetype && (
        <div className="insight-banner">
          <span>
            <strong>{blockRate}%</strong> of decisions this run were blocked outright, and the most common fraud
            pattern was <strong>{formatArchetype(stats.topArchetype.name)}</strong> ({stats.topArchetype.count} cases).
          </span>
        </div>
      )}

      <div className="chart-grid">
        <div className="card">
          <h2 className="with-icon-badge"><span className="icon-badge icon-badge-blue"><BarChart3 /></span>Decisions</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.decisionData}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
              <XAxis dataKey="decision" stroke={AXIS_COLOR} fontSize={12} tickLine={false} axisLine={{ stroke: GRID_COLOR }} />
              <YAxis stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} tickLine={false} axisLine={false} />
              <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                {stats.decisionData.map((entry) => (
                  <Cell key={entry.decision} fill={DECISION_COLORS[entry.decision] || "#999"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="with-icon-badge"><span className="icon-badge icon-badge-purple"><PieChartIcon /></span>Fraud archetypes</h2>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={stats.archetypeData} dataKey="value" nameKey="name" outerRadius={90} label>
                {stats.archetypeData.map((_, i) => (
                  <Cell key={i} fill={ARCHETYPE_COLORS[i % ARCHETYPE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 12, color: AXIS_COLOR }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="with-icon-badge"><span className="icon-badge icon-badge-green"><TrendingUp /></span>Avg risk by event type</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.eventTypeData}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
              <XAxis dataKey="eventType" stroke={AXIS_COLOR} fontSize={11} tickLine={false} axisLine={{ stroke: GRID_COLOR }} />
              <YAxis stroke={AXIS_COLOR} fontSize={12} unit="%" tickLine={false} axisLine={false} />
              <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey="avgRisk" fill="#0B63B0" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="with-icon-badge"><span className="icon-badge icon-badge-blue"><Activity /></span>Risk score distribution</h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={stats.histogramBuckets}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} vertical={false} />
              <XAxis dataKey="bucket" stroke={AXIS_COLOR} fontSize={10} tickLine={false} axisLine={{ stroke: GRID_COLOR }} />
              <YAxis stroke={AXIS_COLOR} fontSize={12} allowDecimals={false} tickLine={false} axisLine={false} />
              <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
              <Bar dataKey="count" fill="#4C93D6" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
