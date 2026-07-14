"use client";
import { clsx } from "clsx";

type Variant = "fraud" | "safe" | "warn" | "info" | "gray";

const VARIANTS: Record<Variant, string> = {
  fraud: "bg-surface-error text-error border border-error/20",
  safe:  "bg-surface-success text-success border border-success/20",
  warn:  "bg-surface-warning text-warning border border-warning/20",
  info:  "bg-secondary-container text-secondary border border-secondary/20",
  gray:  "bg-surface-container text-on-surface-dim border border-outline-variant",
};

interface StatusBadgeProps {
  label: string;
  variant?: Variant;
  dot?: boolean;
  className?: string;
}

export function StatusBadge({ label, variant = "gray", dot = false, className }: StatusBadgeProps) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium",
      VARIANTS[variant],
      className,
    )}>
      {dot && (
        <span className={clsx("w-1.5 h-1.5 rounded-full", {
          "bg-error":    variant === "fraud",
          "bg-success":  variant === "safe",
          "bg-warning":  variant === "warn",
          "bg-secondary":variant === "info",
          "bg-outline":  variant === "gray",
        })} />
      )}
      {label}
    </span>
  );
}

// Helpers for common use-cases
export function AlertSeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, Variant> = {
    critical: "fraud", high: "fraud", medium: "warn", low: "info",
  };
  return <StatusBadge label={severity} variant={map[severity] ?? "gray"} dot />;
}

export function AlertStatusBadge({ status }: { status: string }) {
  const map: Record<string, Variant> = {
    open: "fraud", investigating: "warn",
    resolved: "safe", false_positive: "gray",
  };
  return (
    <StatusBadge
      label={status.replace("_", " ")}
      variant={map[status] ?? "gray"}
      dot
    />
  );
}

export function PredictionBadge({ label }: { label: 0 | 1 }) {
  return label === 1
    ? <StatusBadge label="FRAUD"      variant="fraud" dot />
    : <StatusBadge label="Legitimate" variant="safe"  dot />;
}
