"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { ModelVersion } from "@/types";
import { Sidebar } from "@/components/shared/Sidebar";
import toast from "react-hot-toast";
import { Cpu, CheckCircle, Activity, Zap } from "lucide-react";
import { clsx } from "clsx";
import { formatDistanceToNow } from "date-fns";

export default function ModelsPage() {
  const qc = useQueryClient();

  const { data: models = [], isLoading } = useQuery<ModelVersion[]>({
    queryKey: ["models"],
    queryFn: () => api.get("/models").then((r) => r.data),
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => api.post(`/models/${id}/activate`).then((r) => r.data),
    onSuccess: (data: ModelVersion) => {
      toast.success(`Model ${data.version_tag} is now active`);
      qc.invalidateQueries({ queryKey: ["models"] });
    },
    onError: () => toast.error("Failed to activate model"),
  });

  const fmt = (v: number | null) => (v != null ? `${(v * 100).toFixed(1)}%` : "—");

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-8">
        <div className="mb-6">
          <h1 className="text-headline-md font-headline font-bold text-on-surface">Model Versions</h1>
          <p className="text-body-md text-on-surface-variant mt-1">View training metrics and activate model versions</p>
        </div>

        {isLoading ? (
          <div className="flex justify-center pt-20">
            <div className="w-8 h-8 border-4 border-secondary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : models.length === 0 ? (
          <div className="card p-16 text-center text-on-surface-dim">
            <Cpu className="w-12 h-12 mx-auto mb-4 opacity-30" />
            <p className="font-medium">No models trained yet</p>
            <p className="text-sm mt-1">Run the training pipeline to register a model version</p>
          </div>
        ) : (
          <div className="space-y-4">
            {models.map((m) => (
              <div
                key={m.id}
                className={clsx(
                  "card p-5 border-2 transition-colors",
                  m.is_active ? "border-secondary bg-secondary-container/20" : "border-outline-variant"
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center",
                      m.is_active ? "bg-secondary" : "bg-surface-container")}>
                      <Cpu className={clsx("w-5 h-5", m.is_active ? "text-white" : "text-on-surface-dim")} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-on-surface">{m.version_tag}</h3>
                        {m.is_active && (
                          <span className="flex items-center gap-1 text-xs font-medium text-secondary bg-secondary-container px-2 py-0.5 rounded-full">
                            <CheckCircle className="w-3 h-3" /> Active
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-on-surface-variant mt-0.5 capitalize">
                        {m.algorithm.replace("_", " ")}
                        {m.smote_applied && " + SMOTE"}
                        {" . "}
                        {formatDistanceToNow(new Date(m.trained_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>

                  {!m.is_active && (
                    <button
                      onClick={() => activateMutation.mutate(m.id)}
                      disabled={activateMutation.isPending}
                      className="btn-secondary text-sm flex items-center gap-2"
                    >
                      <Zap className="w-4 h-4" /> Activate
                    </button>
                  )}
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-4 gap-4 mt-5 pt-4 border-t border-outline-variant">
                  {[
                    { label: "Precision", value: fmt(m.precision_score) },
                    { label: "Recall",    value: fmt(m.recall_score) },
                    { label: "F1 Score",  value: fmt(m.f1_score) },
                    { label: "AUC-ROC",   value: fmt(m.auc_roc) },
                  ].map(({ label, value }) => (
                    <div key={label} className="text-center">
                      <p className="text-xl font-bold text-on-surface">{value}</p>
                      <p className="text-xs text-on-surface-dim mt-0.5">{label}</p>
                    </div>
                  ))}
                </div>

                {/* Hyperparams */}
                {Object.keys(m.hyperparams).length > 0 && (
                  <div className="mt-4 pt-3 border-t border-outline-variant">
                    <p className="text-xs font-medium text-on-surface-dim mb-2">Hyperparameters</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(m.hyperparams)
                        .filter(([k]) => !["confusion_matrix", "algorithm"].includes(k))
                        .map(([k, v]) => (
                          <span key={k} className="text-xs bg-surface-container text-on-surface-variant px-2 py-1 rounded font-mono">
                            {k}: {String(v)}
                          </span>
                        ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
