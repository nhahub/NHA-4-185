"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import api from "@/lib/api";
import { PredictionResult } from "@/types";
import { Sidebar } from "@/components/shared/Sidebar";
import { Topbar } from "@/components/shared/Topbar";
import { ProbabilityGauge } from "@/components/charts/ProbabilityGauge";
import { ShapExplanation } from "@/components/shared/ShapExplanation";
import toast from "react-hot-toast";
import { Zap, ShieldCheck, ShieldAlert, Clock, AlertTriangle } from "lucide-react";

const V_FIELDS = Array.from({ length: 28 }, (_, i) => `v${i + 1}`);
const DEFAULTS = Object.fromEntries([["time_seconds","0"],["amount",""],
  ...V_FIELDS.map((f) => [f, "0"])]);

export default function PredictPage() {
  const [form, setForm]   = useState<Record<string, string>>(DEFAULTS);
  const [result, setResult] = useState<PredictionResult | null>(null);

  const mutation = useMutation({
    mutationFn: (data: Record<string, number>) =>
      api.post("/predict/single", data).then((r) => r.data),
    onSuccess: (data: PredictionResult) => {
      setResult(data);
      if (data.is_fraud) toast.error("Fraud detected!");
      else toast.success("Transaction is legitimate");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || "Prediction failed"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = Object.fromEntries(Object.entries(form).map(([k,v]) => [k, parseFloat(v)||0]));
    mutation.mutate(payload);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <Topbar title="Single Prediction" subtitle="Enter transaction features for instant fraud analysis" />

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Form */}
          <div className="card p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Time (seconds)</label>
                  <input type="number" step="any" className="input"
                    value={form.time_seconds} onChange={(e) => setForm({...form,time_seconds:e.target.value})} />
                </div>
                <div>
                  <label className="label">Amount (EUR) *</label>
                  <input type="number" step="any" min="0.01" max="30000" required className="input"
                    placeholder="e.g. 149.62"
                    value={form.amount} onChange={(e) => setForm({...form,amount:e.target.value})} />
                </div>
              </div>
              <div>
                <p className="label">PCA Features V1-V28</p>
                <p className="text-xs text-on-surface-dim mb-2">Accepted range: -30 to +30. Leave at 0 if unknown.</p>
                <div className="grid grid-cols-4 gap-2">
                  {V_FIELDS.map((field) => (
                    <div key={field}>
                      <label className="text-xs text-on-surface-dim mb-0.5 block uppercase">{field}</label>
                      <input type="number" step="any" min="-30" max="30" className="input text-xs py-1.5"
                        value={form[field]} onChange={(e) => setForm({...form,[field]:e.target.value})} />
                    </div>
                  ))}
                </div>
              </div>
              <button type="submit" disabled={mutation.isPending}
                className="btn-primary w-full flex items-center justify-center gap-2">
                <Zap className="w-4 h-4" />
                {mutation.isPending ? "Analyzing..." : "Predict Transaction"}
              </button>
            </form>
          </div>

          {/* Result */}
          <div className="space-y-4">
            {result ? (
              <>
                {/* Verdict */}
                <div className={`card p-6 border-2 ${result.is_fraud ? "border-error bg-surface-error" : "border-success bg-surface-success"}`}>
                  <div className="flex items-center gap-4">
                    {result.is_fraud
                      ? <ShieldAlert className="w-12 h-12 text-error" />
                      : <ShieldCheck className="w-12 h-12 text-success" />}
                    <div>
                      <p className="text-lg font-bold">{result.is_fraud ? "FRAUD DETECTED" : "LEGITIMATE"}</p>
                      <p className="text-sm text-on-surface-variant">Model: {result.model_version}</p>
                    </div>
                    <div className="ml-auto">
                      <ProbabilityGauge probability={result.fraud_probability} threshold={result.decision_threshold} size={140} />
                    </div>
                  </div>
                </div>

                {/* SHAP Explanation */}
                {result.shap_explanation && result.shap_explanation.length > 0 && (
                  <div className="card p-5">
                    <ShapExplanation
                      predictionId={result.prediction_id.toString()}
                      inline={result.shap_explanation}
                    />
                  </div>
                )}

                {/* Meta */}
                <div className="card p-5">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-on-surface-dim">Prediction ID</p>
                      <p className="font-mono text-xs text-on-surface mt-0.5 truncate">{result.prediction_id}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-dim">Latency</p>
                      <div className="flex items-center gap-1 mt-0.5">
                        <Clock className="w-3 h-3 text-on-surface-dim" />
                        <p className="font-semibold text-on-surface">{result.latency_ms.toFixed(1)} ms</p>
                      </div>
                    </div>
                    <div>
                      <p className="text-on-surface-dim">Threshold</p>
                      <p className="font-semibold text-on-surface">{(result.decision_threshold * 100).toFixed(0)}%</p>
                    </div>
                    {result.alert_id && (
                      <div>
                        <p className="text-on-surface-dim">Alert ID</p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-warning" />
                          <a href="/alerts" className="font-mono text-xs text-warning hover:underline">
                            {result.alert_id.toString().slice(0,8)}...
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="card p-12 flex flex-col items-center justify-center text-center text-on-surface-dim h-full min-h-64">
                <Zap className="w-12 h-12 mb-4 opacity-30" />
                <p className="font-medium">No prediction yet</p>
                <p className="text-sm mt-1">Fill in the form and click Predict</p>
                <p className="text-xs mt-3 text-on-surface-dim/50">SHAP explanations will appear after prediction</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
