"use client";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend, Cell,
} from "recharts";
import type { ModelVersion } from "@/types";

interface Props {
  models: ModelVersion[];
  mode?: "radar" | "bar";
}

const COLORS = ["#0266FF", "#00DBE7", "#FCD34D", "#FFB4AB", "#B9C7E4"];

export function ModelMetricsChart({ models, mode = "bar" }: Props) {
  const active = models.filter((m) => m.precision_score !== null);
  if (!active.length) {
    return (
      <div className="flex items-center justify-center h-40 text-sm text-on-surface-dim">
        No model metrics available yet
      </div>
    );
  }

  if (mode === "radar") {
    const m = active.find((m) => m.is_active) || active[0];
    const data = [
      { metric: "Precision", value: m.precision_score ? m.precision_score * 100 : 0 },
      { metric: "Recall",    value: m.recall_score    ? m.recall_score    * 100 : 0 },
      { metric: "F1 Score",  value: m.f1_score        ? m.f1_score        * 100 : 0 },
      { metric: "AUC-ROC",   value: m.auc_roc         ? m.auc_roc         * 100 : 0 },
    ];
    return (
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={data} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
          <PolarGrid stroke="#2A3A4A" />
          <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12, fill: "#8B9BB4" }} />
          <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10, fill: "#6E7F98" }} />
          <Radar
            name={m.version_tag}
            dataKey="value"
            stroke="#00DBE7"
            fill="#00DBE7"
            fillOpacity={0.18}
            strokeWidth={2}
          />
          <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
        </RadarChart>
      </ResponsiveContainer>
    );
  }

  const metrics = ["precision_score", "recall_score", "f1_score", "auc_roc"] as const;
  const labels: Record<string, string> = {
    precision_score: "Precision",
    recall_score: "Recall",
    f1_score: "F1",
    auc_roc: "AUC-ROC",
  };

  const data = metrics.map((key) => ({
    name: labels[key],
    ...Object.fromEntries(
      active.map((m) => [m.version_tag, m[key] ? +(m[key]! * 100).toFixed(2) : 0])
    ),
  }));

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#8B9BB4" }} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#8B9BB4" }} tickFormatter={(v) => `${v}%`}
          axisLine={false} tickLine={false} />
        <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {active.map((m, i) => (
          <Bar
            key={m.id}
            dataKey={m.version_tag}
            fill={COLORS[i % COLORS.length]}
            radius={[4, 4, 0, 0]}
            maxBarSize={48}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
