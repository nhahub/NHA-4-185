"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Sidebar } from "@/components/shared/Sidebar";
import { ClipboardList, Search } from "lucide-react";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

interface AuditLog {
  id: number;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  extra_data: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

const ACTION_COLORS: Record<string, string> = {
  USER_LOGIN:           "bg-secondary-container text-secondary",
  USER_REGISTER:        "bg-surface-success text-success",
  USER_LOGOUT:          "bg-surface-container text-on-surface-dim",
  PREDICT_SINGLE:       "bg-primary-container text-primary",
  PREDICT_BATCH_UPLOAD: "bg-secondary-container text-secondary",
  ALERT_UPDATE:         "bg-surface-warning text-warning",
  MODEL_ACTIVATE:       "bg-tertiary-container text-tertiary",
  ADMIN_USER_UPDATE:    "bg-surface-error text-error",
  ADMIN_USER_DEACTIVATE:"bg-surface-error text-error",
};

export default function AuditLogsPage() {
  const [actionFilter, setActionFilter] = useState("");

  const { data: logs = [], isLoading } = useQuery<AuditLog[]>({
    queryKey: ["audit-logs", actionFilter],
    queryFn: () =>
      api.get("/admin/audit-logs", {
        params: { limit: 200, ...(actionFilter ? { action: actionFilter } : {}) },
      }).then((r) => r.data),
    refetchInterval: 10_000,
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-headline-md font-headline font-bold text-on-surface">Audit Logs</h1>
            <p className="text-body-md text-on-surface-variant mt-1">Immutable record of all user actions</p>
          </div>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-dim" />
            <input
              type="text"
              placeholder="Filter by action..."
              className="input pl-9 w-56 text-sm"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center pt-20">
            <div className="w-8 h-8 border-4 border-secondary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="table-header">
                <tr>
                  {["#", "Action", "Resource", "IP Address", "User ID", "When"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-on-surface-dim uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-surface-container transition-colors">
                    <td className="px-4 py-3 text-xs text-on-surface-dim font-mono">{log.id}</td>
                    <td className="px-4 py-3">
                      <span className={clsx("px-2 py-0.5 rounded-full text-xs font-medium",
                        ACTION_COLORS[log.action] || "bg-surface-container text-on-surface-dim")}>
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-on-surface-variant">
                      {log.resource_type && <span className="capitalize">{log.resource_type}</span>}
                      {log.resource_id && (
                        <span className="font-mono ml-1 text-on-surface-dim">{log.resource_id.slice(0, 8)}...</span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-on-surface-variant">{log.ip_address || "—"}</td>
                    <td className="px-4 py-3 font-mono text-xs text-on-surface-dim">
                      {log.user_id ? `${log.user_id.slice(0, 8)}...` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-on-surface-dim">
                      {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-on-surface-dim">
                      <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-40" />
                      No audit logs yet
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
