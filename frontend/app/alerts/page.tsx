"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { Alert } from "@/types";
import { Sidebar } from "@/components/shared/Sidebar";
import { Topbar } from "@/components/shared/Topbar";
import { ShapExplanation } from "@/components/shared/ShapExplanation";
import toast from "react-hot-toast";
import { AlertTriangle, CheckCircle, Eye, Download } from "lucide-react";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

const STATUS_COLORS: Record<string, string> = {
  open:           "bg-surface-error text-error",
  investigating:  "bg-surface-warning text-warning",
  resolved:       "bg-surface-success text-success",
  false_positive: "bg-surface-container text-on-surface-dim",
};
const SEV_COLORS: Record<string, string> = {
  critical: "bg-surface-error text-error font-bold",
  high:     "bg-surface-error text-error",
  medium:   "bg-surface-warning text-warning",
  low:      "bg-secondary-container text-secondary",
};

interface AlertDetail extends Alert {
  fraud_probability?: number;
  prediction_id?: string;
}

export default function AlertsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<AlertDetail | null>(null);
  const [notes, setNotes] = useState("");

  const { data: alerts = [], isLoading } = useQuery<AlertDetail[]>({
    queryKey: ["alerts", statusFilter],
    queryFn: () =>
      api.get("/alerts", { params: statusFilter ? { status: statusFilter } : {} })
        .then((r) => r.data),
    refetchInterval: 15_000,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: any }) =>
      api.put(`/alerts/${id}`, payload).then((r) => r.data),
    onSuccess: () => {
      toast.success("Alert updated");
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setSelected(null);
    },
  });

  const openCount = alerts.filter((a) => a.status === "open").length;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <Topbar
          title="Fraud Alerts"
          subtitle={`${alerts.length} alerts · ${openCount} open`}
        />

        {/* Filters + export */}
        <div className="flex gap-3 mb-4 flex-wrap items-center">
          <select className="input w-48 text-sm" value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False Positive</option>
          </select>
          <a
            href={`/api/v1/alerts/export${statusFilter ? `?status=${statusFilter}` : ""}`}
            download
            className="btn-secondary text-sm flex items-center gap-1.5 ml-auto"
          >
            <Download className="w-4 h-4" /> Export CSV
          </a>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="flex justify-center pt-20">
            <div className="w-8 h-8 border-4 border-secondary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="table-header">
                <tr>
                  {["Alert ID", "Severity", "Status", "Probability", "Created", "Actions"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-on-surface-dim uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {alerts.map((alert) => (
                  <tr key={alert.id} className="hover:bg-surface-container transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-on-surface-dim">{alert.id.slice(0,8)}...</td>
                    <td className="px-4 py-3">
                      <span className={clsx("px-2 py-0.5 rounded-full text-xs capitalize", SEV_COLORS[alert.severity])}>
                        {alert.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx("px-2 py-0.5 rounded-full text-xs capitalize", STATUS_COLORS[alert.status])}>
                        {alert.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {alert.fraud_probability != null ? (
                        <span className={clsx("font-bold text-sm", alert.fraud_probability > 0.8 ? "text-error" : "text-warning")}>
                          {Math.round(alert.fraud_probability * 100)}%
                        </span>
                      ) : <span className="text-on-surface-dim">—</span>}
                    </td>
                    <td className="px-4 py-3 text-xs text-on-surface-dim">
                      {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => { setSelected(alert); setNotes(alert.notes || ""); }}
                        className="flex items-center gap-1 text-tertiary hover:text-tertiary-hover text-xs font-medium"
                      >
                        <Eye className="w-3.5 h-3.5" /> Review
                      </button>
                    </td>
                  </tr>
                ))}
                {alerts.length === 0 && (
                  <tr><td colSpan={6} className="text-center py-12 text-on-surface-dim">
                    <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-40" />
                    No alerts found
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Review modal */}
        {selected && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
            <div className="card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold text-on-surface">Review Alert</h3>
                <button onClick={() => setSelected(null)} className="text-on-surface-dim hover:text-on-surface text-xl leading-none">X</button>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm mb-4">
                <div className="bg-surface-container rounded-lg p-3">
                  <p className="text-xs text-on-surface-dim mb-0.5">Alert ID</p>
                  <p className="font-mono text-xs text-on-surface">{selected.id.slice(0,16)}...</p>
                </div>
                <div className="bg-surface-container rounded-lg p-3">
                  <p className="text-xs text-on-surface-dim mb-0.5">Severity</p>
                  <span className={clsx("px-2 py-0.5 rounded-full text-xs capitalize", SEV_COLORS[selected.severity])}>
                    {selected.severity}
                  </span>
                </div>
                <div className="bg-surface-container rounded-lg p-3">
                  <p className="text-xs text-on-surface-dim mb-0.5">Status</p>
                  <span className={clsx("px-2 py-0.5 rounded-full text-xs capitalize", STATUS_COLORS[selected.status])}>
                    {selected.status.replace("_", " ")}
                  </span>
                </div>
                {selected.fraud_probability != null && (
                  <div className="bg-surface-error rounded-lg p-3">
                    <p className="text-xs text-on-surface-dim mb-0.5">Fraud probability</p>
                    <p className="text-xl font-bold text-error">{Math.round(selected.fraud_probability * 100)}%</p>
                  </div>
                )}
              </div>

              {selected.prediction_id && (
                <div className="bg-surface-container rounded-xl p-4 mb-4">
                  <ShapExplanation predictionId={selected.prediction_id} />
                </div>
              )}

              <div className="mb-4">
                <label className="label">Investigation notes</label>
                <textarea
                  className="input h-24 resize-none"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Add investigation notes..."
                />
              </div>

              <div className="flex gap-2 flex-wrap">
                <button
                  onClick={() => updateMutation.mutate({ id: selected.id, payload: { status: "investigating", notes } })}
                  className="btn-secondary text-xs flex-1"
                >Set Investigating</button>
                <button
                  onClick={() => updateMutation.mutate({ id: selected.id, payload: { status: "resolved", notes } })}
                  className="btn-primary text-xs flex-1"
                >Mark Resolved</button>
                <button
                  onClick={() => updateMutation.mutate({ id: selected.id, payload: { status: "false_positive", notes } })}
                  className="btn-secondary text-xs flex-1"
                >False Positive</button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
