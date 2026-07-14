import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import Cookies from "js-cookie";
import toast from "react-hot-toast";
import type { User, DashboardStats, Alert, ModelVersion, PredictionResult, TransactionCreate } from "@/types";

// ─── Auth ─────────────────────────────────────────────────────────────────────
export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["me"],
    queryFn: () => api.get("/auth/me").then((r) => r.data),
    retry: false,
    staleTime: 5 * 60_000,
  });
}

export function useLogout() {
  const router = useRouter();
  const qc = useQueryClient();
  return () => {
    api.post("/auth/logout").catch(() => {});
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
    qc.clear();
    router.push("/auth/login");
  };
}

export function useIsAdmin() {
  const { data: user } = useCurrentUser();
  return user?.role === "admin";
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/analytics/dashboard").then((r) => r.data),
    refetchInterval: 30_000,
  });
}

// ─── Prediction ───────────────────────────────────────────────────────────────
export function usePredictSingle() {
  return useMutation<PredictionResult, Error, Record<string, number>>({
    mutationFn: (data) => api.post("/predict/single", data).then((r) => r.data),
    onSuccess: (result) => {
      if (result.is_fraud) {
        toast.error(`⚠️ FRAUD detected! Probability: ${Math.round(result.fraud_probability * 100)}%`);
      } else {
        toast.success(`✅ Legitimate transaction (${Math.round(result.fraud_probability * 100)}% fraud prob)`);
      }
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || "Prediction failed");
    },
  });
}

// ─── Alerts ───────────────────────────────────────────────────────────────────
export function useAlerts(status?: string) {
  return useQuery<Alert[]>({
    queryKey: ["alerts", status],
    queryFn: () =>
      api.get("/alerts", { params: status ? { status } : {} }).then((r) => r.data),
    refetchInterval: 15_000,
  });
}

export function useUpdateAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Alert> }) =>
      api.put(`/alerts/${id}`, payload).then((r) => r.data),
    onSuccess: () => {
      toast.success("Alert updated");
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("Failed to update alert"),
  });
}

// ─── Models ───────────────────────────────────────────────────────────────────
export function useModels() {
  return useQuery<ModelVersion[]>({
    queryKey: ["models"],
    queryFn: () => api.get("/models").then((r) => r.data),
  });
}

export function useActivateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/models/${id}/activate`).then((r) => r.data),
    onSuccess: (data: ModelVersion) => {
      toast.success(`Model ${data.version_tag} is now active`);
      qc.invalidateQueries({ queryKey: ["models"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: () => toast.error("Failed to activate model"),
  });
}

// ─── Health ───────────────────────────────────────────────────────────────────
export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.get("/health").then((r) => r.data),
    refetchInterval: 60_000,
    retry: false,
  });
}

// ─── Analytics ────────────────────────────────────────────────────────────────
export function useFraudTrend(days: number = 7) {
  return useQuery<{ day: string; total: number; fraud: number; fraud_rate: number }[]>({
    queryKey: ["trend", days],
    queryFn: () => api.get(`/analytics/trend?days=${days}`).then((r) => r.data),
    refetchInterval: 60_000,
  });
}

export function useConfusionMatrix() {
  return useQuery<{tn:number;fp:number;fn:number;tp:number;total:number;precision:number|null;recall:number|null;accuracy:number|null}>({
    queryKey: ["confusion-matrix"],
    queryFn: () => api.get("/analytics/confusion-matrix").then((r) => r.data),
  });
}

export function useFraudByAmount() {
  return useQuery<{ bucket: string; total: number; fraud: number; fraud_rate: number }[]>({
    queryKey: ["fraud-by-amount"],
    queryFn: () => api.get("/analytics/fraud-by-amount").then((r) => r.data),
  });
}

export function useTopAlerts(limit = 5) {
  return useQuery<{ alert_id: string; severity: string; fraud_probability: number; created_at: string }[]>({
    queryKey: ["top-alerts", limit],
    queryFn: () => api.get(`/analytics/top-alerts?limit=${limit}`).then((r) => r.data),
    refetchInterval: 15_000,
  });
}

// ─── SHAP / explainability ─────────────────────────────────────────────────
export function usePredictionExplain(predictionId: string | null) {
  return useQuery({
    queryKey: ["explain", predictionId],
    queryFn: () =>
      api.get(`/predict/${predictionId}/explain`).then((r) => r.data),
    enabled: !!predictionId,
    retry: false,
    staleTime: Infinity,
  });
}
