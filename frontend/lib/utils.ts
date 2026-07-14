import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow, parseISO } from "date-fns";

// ─── Tailwind class merger ────────────────────────────────────────────────────
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ─── Number formatting ────────────────────────────────────────────────────────
export function formatCurrency(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatLatency(ms: number): string {
  if (ms < 1) return `${(ms * 1000).toFixed(0)} µs`;
  if (ms < 1000) return `${ms.toFixed(1)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

// ─── Date formatting ──────────────────────────────────────────────────────────
export function formatDate(dateStr: string): string {
  try {
    return format(parseISO(dateStr), "MMM d, yyyy HH:mm");
  } catch {
    return dateStr;
  }
}

export function formatRelative(dateStr: string): string {
  try {
    return formatDistanceToNow(parseISO(dateStr), { addSuffix: true });
  } catch {
    return dateStr;
  }
}

// ─── Fraud severity from probability ─────────────────────────────────────────
export function getSeverity(prob: number): "low" | "medium" | "high" | "critical" {
  if (prob >= 0.95) return "critical";
  if (prob >= 0.80) return "high";
  if (prob >= 0.60) return "medium";
  return "low";
}

export function getSeverityColor(severity: string): string {
  const map: Record<string, string> = {
    low:      "bg-blue-100 text-blue-700",
    medium:   "bg-yellow-100 text-yellow-700",
    high:     "bg-orange-100 text-orange-700",
    critical: "bg-red-100 text-red-800 font-bold",
  };
  return map[severity] ?? "bg-gray-100 text-gray-600";
}

export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    open:          "bg-red-100 text-red-700",
    investigating: "bg-yellow-100 text-yellow-700",
    resolved:      "bg-green-100 text-green-700",
    false_positive:"bg-gray-100 text-gray-600",
  };
  return map[status] ?? "bg-gray-100 text-gray-600";
}

// ─── CSV download helper ──────────────────────────────────────────────────────
export function downloadCSV(rows: Record<string, unknown>[], filename: string): void {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const csvContent = [
    headers.join(","),
    ...rows.map((row) =>
      headers.map((h) => JSON.stringify(row[h] ?? "")).join(",")
    ),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// ─── Truncate text ────────────────────────────────────────────────────────────
export function truncate(str: string, maxLen = 20): string {
  return str.length > maxLen ? `${str.slice(0, maxLen)}…` : str;
}

// ─── Debounce ─────────────────────────────────────────────────────────────────
export function debounce<T extends (...args: unknown[]) => void>(fn: T, delay: number): T {
  let timer: ReturnType<typeof setTimeout>;
  return ((...args: unknown[]) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  }) as T;
}
