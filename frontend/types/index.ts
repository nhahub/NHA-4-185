export interface User {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
}
export interface TokenPair { access_token: string; refresh_token: string; token_type: string; }
export interface TransactionCreate {
  time_seconds: number; amount: number;
  v1: number; v2: number; v3: number; v4: number; v5: number; v6: number; v7: number;
  v8: number; v9: number; v10: number; v11: number; v12: number; v13: number; v14: number;
  v15: number; v16: number; v17: number; v18: number; v19: number; v20: number; v21: number;
  v22: number; v23: number; v24: number; v25: number; v26: number; v27: number; v28: number;
}
export interface Transaction { id: string; time_seconds: number; amount: number; true_label: number | null; source: string; created_at: string; }
export interface TransactionStats { total: number; fraud_count: number; legitimate_count: number; fraud_rate: number; avg_amount: number; }
export interface PredictionResult { prediction_id: string; transaction_id: string; predicted_label: 0 | 1; fraud_probability: number; decision_threshold: number; is_fraud: boolean; alert_id: string | null; latency_ms: number; model_version: string;
  shap_explanation?: ShapFeatureItem[] | null; }
export interface Alert { id: string; prediction_id: string; severity: "low"|"medium"|"high"|"critical"; status: "open"|"investigating"|"resolved"|"false_positive"; assigned_to: string|null; notes: string|null; resolved_at: string|null; created_at: string; }
export interface AlertUpdate { status?: Alert["status"]; assigned_to?: string|null; notes?: string; }
export interface ModelVersion { id: string; version_tag: string; algorithm: string; precision_score: number|null; recall_score: number|null; f1_score: number|null; auc_roc: number|null; smote_applied: boolean; hyperparams: Record<string,unknown>; is_active: boolean; trained_at: string; }
export interface DashboardStats { total_transactions: number; total_fraud: number; fraud_rate: number; precision: number|null; recall: number|null; auc_roc: number|null; pr_auc: number|null; mcc: number|null; open_alerts: number; today_transactions: number; today_fraud: number; }
export interface BatchJobStatus { job_id: string; status: "pending"|"started"|"completed"|"failed"; total?: number; processed?: number; fraud_count?: number; }
export interface HealthStatus { status: "ok"|"degraded"|"error"; database: string; redis: string; ml_model: string;
  shap_loaded: boolean; version: string; }
export interface TrendPoint { label: string; transactions: number; fraud: number; fraud_rate?: number; }
export interface AuditLog { id: number; user_id: string|null; action: string; resource_type: string|null; resource_id: string|null; extra_data: Record<string,unknown>; ip_address: string|null; created_at: string; }

export interface ShapFeatureItem {
  feature: string;
  value: number;
  shap_value: number;
  direction: "fraud" | "legitimate";
}
