"use client";
import { clsx } from "clsx";
import { AlertTriangle, Inbox, ArrowUpCircle, ArrowDownCircle, TrendingUp, TrendingDown, Minus, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";
import { HealthStatusBar } from "./HealthStatusBar";
import { Topbar } from "./Topbar";
import { Sidebar } from "./Sidebar";

export function LoadingSpinner({ className, size = "md" }: { className?: string; size?: "sm" | "md" | "lg" }) {
  const s = size === "lg" ? "h-10 w-10" : size === "sm" ? "h-4 w-4" : "h-6 w-6";
  return (
    <div className={clsx("flex items-center justify-center", className)}>
      <div className={clsx("animate-spin rounded-full border-2 border-outline-variant border-t-tertiary", s)} />
    </div>
  );
}

export function LoadingPage() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <LoadingSpinner size="lg" />
      <p className="text-on-surface-variant text-sm animate-pulse">Loading...</p>
    </div>
  );
}

export function ErrorAlert({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-start gap-3 p-4 bg-surface-error border border-error/30 rounded-lg text-on-container-error">
      <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm">{message}</p>
      </div>
      {onRetry && (
        <button onClick={onRetry} className="text-sm font-medium underline hover:no-underline">
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description, icon: Icon = Inbox }: { title: string; description?: string; icon?: React.ComponentType<{ className?: string }> }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 bg-surface-container rounded-full flex items-center justify-center mb-4">
        <Icon className="w-7 h-7 text-on-surface-dim" />
      </div>
      <h3 className="text-headline-sm font-headline font-semibold text-on-surface mb-1">{title}</h3>
      {description && <p className="text-body-md text-on-surface-variant max-w-sm">{description}</p>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between pb-6 border-b border-outline-variant mb-6">
      <div>
        <h1 className="text-headline-md font-headline font-bold text-on-surface">{title}</h1>
        {subtitle && <p className="text-body-md text-on-surface-variant mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function HealthDot({ status }: { status: boolean | null }) {
  return (
    <span className={clsx(
      "w-2 h-2 rounded-full shrink-0",
      status === true ? "bg-success" : status === false ? "bg-error" : "bg-outline animate-pulse",
    )} />
  );
}

export function StatCard({ title, value, icon, color = "blue", loading = false, onClick }: {
  title: string; value: string | number; icon?: React.ReactNode;
  color?: "blue" | "red" | "green" | "amber" | "purple" | "gray";
  loading?: boolean; onClick?: () => void;
}) {
  const colorMap: Record<string, string> = {
    blue:   "text-secondary",
    red:    "text-error",
    green:  "text-success",
    amber:  "text-warning",
    purple: "text-tertiary",
    gray:   "text-on-surface-dim",
  };
  return (
    <div className={clsx("card p-5", onClick && "cursor-pointer hover:border-outline transition-all")} onClick={onClick}>
      {loading ? (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 w-20 bg-surface-container rounded" />
          <div className="h-7 w-16 bg-surface-container rounded" />
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-2">
            <p className="text-label-md uppercase tracking-wider text-on-surface-variant">{title}</p>
            {icon && <span className={colorMap[color]}>{icon}</span>}
          </div>
          <p className="text-headline-md font-headline font-bold text-on-surface">{value}</p>
        </>
      )}
    </div>
  );
}

export function Badge({ children, variant = "default", className }: {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info";
  className?: string;
}) {
  const map: Record<string, string> = {
    default: "bg-surface-container text-on-surface-variant border-outline-variant",
    success: "bg-surface-success text-success border-success/20",
    warning: "bg-surface-warning text-warning border-warning/20",
    error:   "bg-surface-error text-error border-error/20",
    info:    "bg-secondary-container text-secondary border-secondary/20",
  };
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded-full text-label-sm border", map[variant], className)}>
      {children}
    </span>
  );
}

export function TrendIndicator({ value, suffix = "" }: { value: number; suffix?: string }) {
  if (value > 0) return (
    <span className="inline-flex items-center gap-0.5 text-success text-xs font-medium">
      <TrendingUp className="w-3 h-3" /> +{value.toFixed(1)}{suffix}
    </span>
  );
  if (value < 0) return (
    <span className="inline-flex items-center gap-0.5 text-error text-xs font-medium">
      <TrendingDown className="w-3 h-3" /> {value.toFixed(1)}{suffix}
    </span>
  );
  return (
    <span className="inline-flex items-center gap-0.5 text-on-surface-dim text-xs">
      <Minus className="w-3 h-3" /> 0{suffix}
    </span>
  );
}

export function Pagination({ page, totalPages, onPageChange }: {
  page: number; totalPages: number; onPageChange: (p: number) => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t border-outline-variant">
      <p className="text-body-sm text-on-surface-variant">
        Page {page} of {totalPages}
      </p>
      <div className="flex items-center gap-1">
        <button onClick={() => onPageChange(1)} disabled={page <= 1}
          className="p-1.5 rounded-md text-on-surface-variant hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
          <ChevronsLeft className="w-4 h-4" />
        </button>
        <button onClick={() => onPageChange(page - 1)} disabled={page <= 1}
          className="p-1.5 rounded-md text-on-surface-variant hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
          <ChevronLeft className="w-4 h-4" />
        </button>
        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
          let p: number;
          if (totalPages <= 5) p = i + 1;
          else if (page <= 3) p = i + 1;
          else if (page >= totalPages - 2) p = totalPages - 4 + i;
          else p = page - 2 + i;
          return (
            <button key={p} onClick={() => onPageChange(p)}
              className={clsx("w-8 h-8 rounded-md text-sm font-medium transition-colors",
                p === page ? "bg-secondary-container text-on-secondary-container" : "text-on-surface-variant hover:bg-surface-container"
              )}>
              {p}
            </button>
          );
        })}
        <button onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}
          className="p-1.5 rounded-md text-on-surface-variant hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
          <ChevronRight className="w-4 h-4" />
        </button>
        <button onClick={() => onPageChange(totalPages)} disabled={page >= totalPages}
          className="p-1.5 rounded-md text-on-surface-variant hover:bg-surface-container disabled:opacity-30 disabled:cursor-not-allowed transition-colors">
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

export function DataTable({ columns, data, onRowClick, emptyMessage = "No data available" }: {
  columns: { key: string; label: string; className?: string; render?: (v: any, row: any) => React.ReactNode }[];
  data: any[];
  onRowClick?: (row: any) => void;
  emptyMessage?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="table-header">
            {columns.map((col) => (
              <th key={col.key} className={clsx("px-4 py-3 text-left text-label-caps uppercase tracking-wider", col.className)}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-on-surface-variant">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr key={row.id ?? i}
                className={clsx("table-row", onRowClick && "cursor-pointer")}
                onClick={() => onRowClick?.(row)}>
                {columns.map((col) => (
                  <td key={col.key} className={clsx("table-cell", col.className)}>
                    {col.render ? col.render(row[col.key], row) : (row[col.key] ?? "–")}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export { Topbar, Sidebar, HealthStatusBar };
