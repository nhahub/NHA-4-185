"use client";
import { useHealth } from "@/hooks";
import { clsx } from "clsx";
import { Database, Server, Cpu, Brain } from "lucide-react";

export function HealthStatusBar() {
  const { data, isError } = useHealth();

  const services = [
    { label: "Database", value: data?.database,   icon: Database },
    { label: "Redis",    value: data?.redis,       icon: Server   },
    { label: "ML Model", value: data?.ml_model,    icon: Cpu      },
    { label: "SHAP",
      value: data?.shap_loaded === undefined ? undefined
           : data.shap_loaded ? "loaded" : "unavailable",
      icon: Brain },
  ];

  const isOk = (v?: string) => v === "ok" || v === "loaded";

  return (
    <div className="flex items-center gap-3">
      {services.map(({ label, value, icon: Icon }) => (
        <div key={label} className="flex items-center gap-1.5 text-xs"
             title={`${label}: ${value ?? "checking..."}`}>
          <div className={clsx(
            "w-1.5 h-1.5 rounded-full",
            isError || !value        ? "bg-outline animate-pulse"
            : isOk(value)            ? "bg-success"
            : value === "unavailable" ? "bg-warning"
            : "bg-error animate-pulse"
          )} />
          <Icon className="w-3 h-3 text-on-surface-dim" />
          <span className="text-on-surface-dim hidden sm:inline">{label}</span>
        </div>
      ))}
    </div>
  );
}
