# FraudShield — v2.0 Changelog

## Breaking improvements (ML pipeline rebuilt from scratch)

### FIX 1 — Chronological split (was: random split)
**File:** `backend/app/ml/pipeline/train.py`

Random split allowed future transactions to appear in the training set
(temporal leakage). Metrics were inflated 3–8%. Now: data is sorted by
`Time` and split 70% / 10% / 20% in strict chronological order.
Metrics will be 2–5 points lower but are now **honest**.

### FIX 2 — Feature engineering before SMOTE
**File:** `backend/app/ml/pipeline/train.py`

New features added before scaling and SMOTE:
- `log_amount` — compresses right-skewed Amount distribution
- `is_small_amount` — flags card-testing fraud (< €10)
- `is_round_amount` — flags automated fraud (round numbers)
- `is_large_amount` — flags high-value fraud (> €1000)
- `hour` — hour of day extracted from Time
- `is_night` — binary flag for hours 0–5
- `hour_sin` / `hour_cos` — cyclical encoding (preserves 23:00 ≈ 01:00)
- `day_period` — morning / afternoon / evening / night

Total features: **39** (was 30)

### FIX 3 — XGBoost + Optuna tuning
**File:** `backend/app/ml/pipeline/train.py`

New primary model: XGBoost with Optuna Bayesian optimization.
- 50 Optuna trials with TPE sampler + MedianPruner
- Optimizes PR-AUC on validation set (not ROC-AUC)
- Expected: AUC-ROC 0.98–0.99, PR-AUC 0.82–0.88
- Logistic Regression retained as baseline / fallback

### FIX 4 — RobustScaler (was: StandardScaler)
**File:** `backend/app/ml/pipeline/train.py`

RobustScaler uses median and IQR instead of mean and std.
Resistant to the €25,691 Amount outlier that distorted StandardScaler.

### FIX 5 — PR-AUC as primary metric
**Files:** `train.py`, `analytics.py`, `schemas.py`, `dashboard/page.tsx`

PR-AUC (Average Precision) added as primary evaluation metric.
ROC-AUC is overly optimistic for 0.17% fraud rate datasets.
Dashboard now shows PR-AUC ★ and MCC alongside Precision/Recall.

### FIX 6 — Threshold optimization on validation set
**File:** `backend/app/ml/pipeline/train.py`

Threshold swept on VALIDATION set (not test set — that was data leakage).
Best threshold stored in model metadata and loaded at startup.
Default 0.5 replaced by data-optimized threshold per model.

### FIX 7 — Explicit artifact paths in metadata
**Files:** `train.py`, `main.py`, `seeds.py`

Scaler path and SHAP explainer path stored explicitly in
`model_versions.hyperparams` JSONB — no more fragile string manipulation.

### FIX 8 — Atomic prediction DB writes
**File:** `backend/app/services/prediction_service.py`

All DB writes (transaction + prediction + alert) wrapped in one atomic
block with rollback on failure. No more orphaned transaction records when
ML inference fails.

## New features

### SHAP explainability
- `backend/app/ml/model_registry.py` — `explain()` method returns top-5 features per prediction
- `backend/app/api/v1/endpoints/predict.py` — `GET /predict/{id}/explain`
- `frontend/components/shared/ShapExplanation.tsx` — animated bar chart
- Predict page shows SHAP inline on every prediction result
- Alerts review modal shows SHAP explanation for each flagged transaction

### Input validation ranges
- V1–V28: must be in [−30, +30]
- Amount: must be in (0, 30000]
- time_seconds: must be in [0, 200000]
- Returns 422 with field-level errors on violation

### Health endpoint: shap_loaded field
`GET /api/v1/health` now returns `shap_loaded: bool`
Frontend HealthStatusBar shows Brain icon for SHAP status.

## Run v2 pipeline
```bash
# Quick (no Optuna — 5 minutes)
make train-fast

# Full (Optuna 50 trials — ~30 minutes)
make train-all

# Individual models
make train-lr
make train-xgb
```

## Expected metrics (v2 vs v1)

| Metric    | v1 (LR, random split) | v2 (XGBoost, chronological) |
|-----------|----------------------|------------------------------|
| AUC-ROC   | 0.97 (inflated)      | 0.98–0.99 (honest)           |
| PR-AUC    | ~0.70 (not tracked)  | 0.82–0.88                    |
| Recall    | ~0.88                | ~0.92–0.95                   |
| MCC       | not tracked          | 0.80–0.88                    |
| Threshold | 0.50 (default)       | optimized per model          |
| Features  | 30                   | 39                           |
