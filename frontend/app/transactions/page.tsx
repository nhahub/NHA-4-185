"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { Sidebar } from "@/components/shared/Sidebar";
import { CreditCard, Search, Filter } from "lucide-react";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

interface Transaction {
  id: string;
  time_seconds: number;
  amount: number;
  true_label: number | null;
  source: string;
  created_at: string;
}

interface Stats {
  total: number;
  fraud_count: number;
  legitimate_count: number;
  fraud_rate: number;
  avg_amount: number;
}

export default function TransactionsPage() {
  const [fraudOnly, setFraudOnly] = useState(false);
  const [amountMin, setAmountMin] = useState("");
  const [amountMax, setAmountMax] = useState("");

  const params: Record<string, string> = { limit: "100" };
  if (fraudOnly) params.fraud_only = "true";
  if (amountMin) params.amount_min = amountMin;
  if (amountMax) params.amount_max = amountMax;

  const { data: transactions = [], isLoading } = useQuery<Transaction[]>({
    queryKey: ["transactions", params],
    queryFn: () => api.get("/transactions", { params }).then((r) => r.data),
  });

  const { data: stats } = useQuery<Stats>({
    queryKey: ["transaction-stats"],
    queryFn: () => api.get("/transactions/stats").then((r) => r.data),
    refetchInterval: 30_000,
  });

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-6">
          <h1 className="text-headline-md font-headline font-bold text-on-surface">Transactions</h1>
          <p className="text-body-md text-on-surface-variant mt-1">All transactions processed by the system</p>
        </div>

        {/* Stats strip */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
            {[
              { label: "Total",       value: stats.total.toLocaleString(),             color: "text-on-surface" },
              { label: "Fraud",       value: stats.fraud_count.toLocaleString(),       color: "text-error" },
              { label: "Legitimate",  value: stats.legitimate_count.toLocaleString(),  color: "text-success" },
              { label: "Fraud Rate",  value: `${(stats.fraud_rate * 100).toFixed(3)}%`, color: "text-warning" },
              { label: "Avg Amount",  value: `$${stats.avg_amount.toFixed(2)}`,        color: "text-secondary" },
            ].map(({ label, value, color }) => (
              <div key={label} className="card p-3 text-center">
                <p className={`text-xl font-bold ${color}`}>{value}</p>
                <p className="text-xs text-on-surface-dim mt-0.5">{label}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="card p-4 mb-4 flex flex-wrap gap-4 items-end">
          <div>
            <label className="label text-xs">Min amount ($)</label>
            <input
              type="number" min="0" step="0.01"
              className="input w-32 text-sm"
              placeholder="0.00"
              value={amountMin}
              onChange={(e) => setAmountMin(e.target.value)}
            />
          </div>
          <div>
            <label className="label text-xs">Max amount ($)</label>
            <input
              type="number" min="0" step="0.01"
              className="input w-32 text-sm"
              placeholder="any"
              value={amountMax}
              onChange={(e) => setAmountMax(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={fraudOnly}
              onChange={(e) => setFraudOnly(e.target.checked)}
              className="w-4 h-4 accent-error"
            />
            <span className="text-sm font-medium text-on-surface-variant">Fraud only</span>
          </label>
          <button
            onClick={() => { setAmountMin(""); setAmountMax(""); setFraudOnly(false); }}
            className="btn-secondary text-xs"
          >
            Clear filters
          </button>
          <a
            href={`/api/v1/transactions/export${fraudOnly ? "?fraud_only=true" : ""}`}
            download
            className="btn-secondary text-xs flex items-center gap-1.5 ml-auto"
          >
            Export CSV
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
                  {["Transaction ID", "Amount", "Time (s)", "Source", "Label", "Created"].map((h) => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-on-surface-dim uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-surface-container transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-on-surface-dim">{tx.id.slice(0, 8)}...</td>
                    <td className="px-4 py-3 font-semibold text-on-surface">${Number(tx.amount).toFixed(2)}</td>
                    <td className="px-4 py-3 text-on-surface-variant">{tx.time_seconds.toFixed(0)}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded-full text-xs bg-surface-container text-on-surface-variant capitalize">{tx.source}</span>
                    </td>
                    <td className="px-4 py-3">
                      {tx.true_label === null ? (
                        <span className="text-xs text-on-surface-dim">—</span>
                      ) : tx.true_label === 1 ? (
                        <span className="badge-fraud">Fraud</span>
                      ) : (
                        <span className="badge-safe">Legit</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-on-surface-dim">
                      {formatDistanceToNow(new Date(tx.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                ))}
                {transactions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-on-surface-dim">
                      <CreditCard className="w-8 h-8 mx-auto mb-2 opacity-40" />
                      No transactions found
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
