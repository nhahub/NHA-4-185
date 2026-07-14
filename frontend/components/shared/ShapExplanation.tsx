"use client";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { clsx } from "clsx";
import { Loader2, Info } from "lucide-react";

interface ShapFeature {
  feature: string;
  value: number;
  shap_value: number;
  direction: "fraud" | "legitimate";
}

interface ShapExplanationProps {
  predictionId: string;
  inline?: ShapFeature[];
  className?: string;
}

const FEATURE_LABELS: Record<string, string> = {
  V14: "PCA Feature 14 (top fraud signal)",
  V4:  "PCA Feature 4",
  V12: "PCA Feature 12",
  V10: "PCA Feature 10",
  V11: "PCA Feature 11",
  V17: "PCA Feature 17",
  V3:  "PCA Feature 3",
  log_amount:      "Transaction amount (log)",
  is_night:        "Night-time transaction",
  is_small_amount: "Small amount (<EUR10)",
  is_round_amount: "Round amount",
  is_large_amount: "Large amount (>EUR1000)",
  hour:            "Hour of day",
  Amount:          "Transaction amount (EUR)",
  Time:            "Time since first transaction",
};

function label(feature: string) {
  return FEATURE_LABELS[feature] ?? feature;
}

export function ShapExplanation({ predictionId, inline, className }: ShapExplanationProps) {
  const { data, isLoading, isError } = useQuery<{
    explanation: ShapFeature[];
    predicted_label: number;
    fraud_probability: number;
  }>({
    queryKey: ["shap", predictionId],
    queryFn:  () => api.get(`/predict/${predictionId}/explain`).then((r) => r.data),
    enabled:  !inline,
    retry:    false,
    staleTime: Infinity,
  });

  const features: ShapFeature[] = inline ?? data?.explanation ?? [];

  if (!inline && isLoading) {
    return (
      <div className={clsx("flex items-center gap-2 text-sm text-on-surface-dim py-3", className)}>
        <Loader2 className="w-4 h-4 animate-spin" />
        Computing SHAP explanation...
      </div>
    );
  }

  if (!inline && isError) {
    return (
      <div className={clsx("text-xs text-on-surface-dim py-2", className)}>
        SHAP explanation unavailable — train model with XGBoost to enable
      </div>
    );
  }

  if (!features.length) return null;

  const maxAbs = Math.max(...features.map((f) => Math.abs(f.shap_value)));

  return (
    <div className={clsx("space-y-2", className)}>
      <div className="flex items-center gap-1.5 mb-3">
        <Info className="w-3.5 h-3.5 text-on-surface-dim" />
        <p className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">
          Why this transaction was flagged
        </p>
      </div>

      {features.map((feat) => {
        const pct = Math.abs(feat.shap_value) / maxAbs * 100;
        const isFraud = feat.direction === "fraud";
        return (
          <div key={feat.feature}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-on-surface font-medium">{label(feat.feature)}</span>
              <span className={clsx("font-semibold", isFraud ? "text-error" : "text-success")}>
                {isFraud ? "fraud" : "legit"}&nbsp;
                {feat.shap_value > 0 ? "+" : ""}{feat.shap_value.toFixed(3)}
              </span>
            </div>
            <div className="h-2 bg-surface-container rounded-full overflow-hidden">
              <div
                className={clsx("h-full rounded-full transition-all", isFraud ? "bg-error/70" : "bg-success/70")}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}

      <p className="text-[10px] text-on-surface-dim mt-2">
        SHAP values show how much each feature pushed the prediction toward fraud (red) or legitimate (green).
      </p>
    </div>
  );
}
