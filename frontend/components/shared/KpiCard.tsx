"use client";
import { clsx } from "clsx";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon?: React.ReactNode;
  trend?: number;
  trendLabel?: string;
  color?: "blue" | "red" | "green" | "amber" | "purple" | "gray";
  loading?: boolean;
}

const COLOR_MAP = {
  blue:   { bg: "bg-secondary-container", icon: "text-secondary"  },
  red:    { bg: "bg-surface-error",        icon: "text-error"      },
  green:  { bg: "bg-surface-success",      icon: "text-success"    },
  amber:  { bg: "bg-surface-warning",      icon: "text-warning"    },
  purple: { bg: "bg-primary-container",    icon: "text-primary"    },
  gray:   { bg: "bg-surface-container",    icon: "text-on-surface-dim" },
};

export function KpiCard({
  label, value, sub, icon, trend, trendLabel,
  color = "blue", loading = false,
}: KpiCardProps) {
  const c = COLOR_MAP[color];

  return (
    <div className="card p-5">
      {loading ? (
        <div className="space-y-3 animate-pulse">
          <div className="h-3 w-24 bg-surface-container rounded" />
          <div className="h-7 w-16 bg-surface-container rounded" />
          <div className="h-3 w-20 bg-surface-container rounded" />
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between mb-3">
            <p className="text-label-md uppercase tracking-wider text-on-surface-variant">{label}</p>
            {icon && (
              <div className={clsx("w-9 h-9 rounded-lg flex items-center justify-center", c.bg)}>
                <span className={clsx("[&>svg]:w-4 [&>svg]:h-4", c.icon)}>{icon}</span>
              </div>
            )}
          </div>

          <p className="text-headline-lg font-headline font-bold text-on-surface tracking-tight">{value}</p>

          {(sub || trend !== undefined) && (
            <div className="flex items-center gap-2 mt-2">
              {trend !== undefined && (
                <span className={clsx(
                  "flex items-center gap-0.5 text-xs font-medium",
                  trend > 0 ? "text-error" : trend < 0 ? "text-success" : "text-on-surface-dim"
                )}>
                  {trend > 0 ? <TrendingUp className="w-3 h-3" />
                   : trend < 0 ? <TrendingDown className="w-3 h-3" />
                   : <Minus className="w-3 h-3" />}
                  {Math.abs(trend)}%
                </span>
              )}
              {sub && <p className="text-xs text-on-surface-dim">{sub}</p>}
              {trendLabel && <p className="text-xs text-on-surface-dim">{trendLabel}</p>}
            </div>
          )}
        </>
      )}
    </div>
  );
}
