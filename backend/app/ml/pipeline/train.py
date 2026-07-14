"""
FraudShield — Production ML Training Pipeline
===============================================
Run:  python -m app.ml.pipeline.train
      python -m app.ml.pipeline.train --model xgboost
      python -m app.ml.pipeline.train --model all --tune

Fixes applied vs v1:
  ✅ FIX 1 — Chronological split (no temporal leakage)
  ✅ FIX 2 — Feature engineering BEFORE SMOTE (log_amount, is_night, hour)
  ✅ FIX 3 — XGBoost with Optuna tuning + SHAP explainability
  ✅ FIX 4 — RobustScaler on Amount (outlier-resistant)
  ✅ FIX 5 — PR-AUC as primary metric (not ROC-AUC)
  ✅ FIX 6 — Threshold sweep on VALIDATION set (not test)
  ✅ FIX 7 — Explicit artifact paths stored in metadata
  ✅ FIX 8 — MCC added as supplementary metric
"""

import argparse
import json
import time
import warnings
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, f1_score, precision_score, recall_score,
    average_precision_score, matthews_corrcoef,
    precision_recall_curve,
)
from imblearn.over_sampling import SMOTE

warnings.filterwarnings("ignore")

# ── Optional imports (graceful degradation) ───────────────────────────────────
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("[Warning] XGBoost not installed. Run: pip install xgboost")

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False
    print("[Warning] Optuna not installed. Run: pip install optuna")

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
    print("[Warning] SHAP not installed. Run: pip install shap")

# ── Paths ─────────────────────────────────────────────────────────────────────
ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_PATH = Path(__file__).parents[4] / "ml" / "data" / "creditcard.csv"
RANDOM_STATE = 42


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 1 — Load & Validate
# ══════════════════════════════════════════════════════════════════════════════
def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"\n[Error] Dataset not found: {path}\n"
            "Download from: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud\n"
            "Place at: ml/data/creditcard.csv"
        )
    df = pd.read_csv(path)

    # Validate schema
    required = ["Time", "Amount", "Class"] + [f"V{i}" for i in range(1, 29)]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"[Error] Missing columns: {missing_cols}")

    # Remove duplicates (keep first by Time)
    before = len(df)
    df = df.sort_values("Time").drop_duplicates().reset_index(drop=True)
    removed = before - len(df)

    print(f"\n[Stage 1] Dataset loaded")
    print(f"  Rows: {len(df):,} ({removed} duplicates removed)")
    print(f"  Fraud: {df['Class'].sum():,} ({df['Class'].mean():.4%})")
    print(f"  Time range: {df['Time'].min():.0f}s – {df['Time'].max():.0f}s")
    print(f"  Amount range: €{df['Amount'].min():.2f} – €{df['Amount'].max():.2f}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 2 — Feature Engineering (FIX 2: before scaling and SMOTE)
# ══════════════════════════════════════════════════════════════════════════════
def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Add engineered features to the dataframe.
    Must run BEFORE scaling and BEFORE SMOTE.
    """
    df = df.copy()

    # ── Amount features ───────────────────────────────────────────────────────
    df["log_amount"]      = np.log1p(df["Amount"])          # compress right skew
    df["is_small_amount"] = (df["Amount"] < 10).astype(int) # card-testing flag
    df["is_round_amount"] = (df["Amount"] % 10 == 0).astype(int)  # automated fraud
    df["is_large_amount"] = (df["Amount"] > 1000).astype(int)

    # ── Time features ─────────────────────────────────────────────────────────
    # Data spans ~48 hours — map seconds to hour of day
    df["hour"]     = (df["Time"] % 86400 // 3600).astype(int)
    df["is_night"] = df["hour"].isin([0, 1, 2, 3, 4, 5]).astype(int)

    # Cyclical encoding — preserves continuity between 23:00 and 01:00
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)

    # Day period (coarser bucket)
    def get_period(h):
        if h < 6:   return 0  # night
        if h < 12:  return 1  # morning
        if h < 18:  return 2  # afternoon
        return 3              # evening
    df["day_period"] = df["hour"].apply(get_period)

    # ── Feature list (ordered) ────────────────────────────────────────────────
    v_cols  = [f"V{i}" for i in range(1, 29)]
    eng_cols = [
        "log_amount", "is_small_amount", "is_round_amount", "is_large_amount",
        "hour", "is_night", "hour_sin", "hour_cos", "day_period",
    ]
    # Keep original Amount and Time for scaler compatibility
    feature_cols = ["Time", "Amount"] + v_cols + eng_cols

    print(f"\n[Stage 2] Feature engineering complete")
    print(f"  Original features:    30")
    print(f"  Engineered features:  {len(eng_cols)}")
    print(f"  Total features:       {len(feature_cols)}")
    print(f"  Fraud night rate:     {df[df['Class']==1]['is_night'].mean():.1%}")
    print(f"  Legit night rate:     {df[df['Class']==0]['is_night'].mean():.1%}")
    print(f"  Small amount fraud:   {df[df['Class']==1]['is_small_amount'].mean():.1%}")

    return df, feature_cols


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 3 — Chronological Split (FIX 1: no temporal leakage)
# ══════════════════════════════════════════════════════════════════════════════
def chronological_split(df: pd.DataFrame, feature_cols: list[str]):
    """
    Split by transaction TIME order — not randomly.

    Why: In production, the model always predicts future transactions.
    Random split lets future data leak into training — inflates AUC-ROC by 3-8%.

    Split: 70% train | 10% validation | 20% test
    Data is already sorted by Time from load_data().
    """
    n = len(df)
    train_end = int(n * 0.70)
    val_end   = int(n * 0.80)

    df_train = df.iloc[:train_end]
    df_val   = df.iloc[train_end:val_end]
    df_test  = df.iloc[val_end:]

    X_train = df_train[feature_cols].values
    X_val   = df_val[feature_cols].values
    X_test  = df_test[feature_cols].values
    y_train = df_train["Class"].values
    y_val   = df_val["Class"].values
    y_test  = df_test["Class"].values

    print(f"\n[Stage 3] Chronological split (NO random shuffle)")
    print(f"  Train: {len(X_train):>7,} rows | fraud: {y_train.sum():>4} ({y_train.mean():.4%})")
    print(f"  Val:   {len(X_val):>7,} rows | fraud: {y_val.sum():>4} ({y_val.mean():.4%})")
    print(f"  Test:  {len(X_test):>7,} rows | fraud: {y_test.sum():>4} ({y_test.mean():.4%})")

    return X_train, X_val, X_test, y_train, y_val, y_test


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 4 — Scaling (FIX 4: RobustScaler on Amount)
# ══════════════════════════════════════════════════════════════════════════════
def scale_features(X_train, X_val, X_test, feature_cols: list[str]):
    """
    Scale only the features that need it.
    V1-V28: already PCA-normalized — do NOT rescale.
    Amount, Time, log_amount: scale with RobustScaler (outlier-resistant).
    Binary flags (is_night, etc.): already in [0,1] — no scaling.
    """
    # Indices of features to scale
    scale_indices = [
        feature_cols.index("Time"),
        feature_cols.index("Amount"),
        feature_cols.index("log_amount"),
        feature_cols.index("hour"),
        feature_cols.index("hour_sin"),
        feature_cols.index("hour_cos"),
        feature_cols.index("day_period"),
    ]

    scaler = RobustScaler()  # resistant to Amount outliers (€25K+)
    X_train_s = X_train.copy()
    X_val_s   = X_val.copy()
    X_test_s  = X_test.copy()

    X_train_s[:, scale_indices] = scaler.fit_transform(X_train[:, scale_indices])
    X_val_s[:, scale_indices]   = scaler.transform(X_val[:, scale_indices])
    X_test_s[:, scale_indices]  = scaler.transform(X_test[:, scale_indices])

    scaler_path = ARTIFACTS_DIR / "scaler.pkl"
    joblib.dump(scaler, scaler_path)

    print(f"\n[Stage 4] RobustScaler fitted on training set only")
    print(f"  Scaled {len(scale_indices)} features | Saved: {scaler_path.name}")

    return X_train_s, X_val_s, X_test_s, scaler, scale_indices


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 5 — SMOTE (on SCALED training set only)
# ══════════════════════════════════════════════════════════════════════════════
def apply_smote(X_train_s, y_train):
    """
    SMOTE applied AFTER feature engineering and scaling.
    Never applied to validation or test sets.
    """
    smote = SMOTE(k_neighbors=5, random_state=RANDOM_STATE, n_jobs=-1)
    X_res, y_res = smote.fit_resample(X_train_s, y_train)

    print(f"\n[Stage 5] SMOTE applied to TRAINING SET ONLY")
    print(f"  Before: {len(X_train_s):,} rows | fraud: {y_train.sum():,}")
    print(f"  After:  {len(X_res):,} rows | fraud: {y_res.sum():,}")
    return X_res, y_res


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 6 — Threshold Optimization (FIX 6: on VALIDATION set)
# ══════════════════════════════════════════════════════════════════════════════
def optimize_threshold(model, X_val, y_val) -> tuple[float, float]:
    """
    Sweep threshold on VALIDATION set (not test set — that's data leakage).
    Optimize for F1 score. Returns (best_threshold, best_f1).
    """
    probas = model.predict_proba(X_val)[:, 1]
    best_threshold, best_f1 = 0.5, 0.0

    for t in np.arange(0.05, 0.95, 0.005):
        preds = (probas >= t).astype(int)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_threshold = float(t)

    return best_threshold, best_f1


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 7 — Evaluation Metrics (FIX 5 & 8: PR-AUC + MCC)
# ══════════════════════════════════════════════════════════════════════════════
def evaluate(model, X_test, y_test, threshold: float, label: str) -> dict:
    """Full evaluation on untouched test set."""
    probas = model.predict_proba(X_test)[:, 1]
    preds  = (probas >= threshold).astype(int)
    cm     = confusion_matrix(y_test, preds)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "algorithm":       label,
        "threshold":       round(threshold, 3),
        "precision":       round(float(precision_score(y_test, preds, zero_division=0)), 4),
        "recall":          round(float(recall_score(y_test, preds, zero_division=0)), 4),
        "f1":              round(float(f1_score(y_test, preds, zero_division=0)), 4),
        "auc_roc":         round(float(roc_auc_score(y_test, probas)), 4),
        "pr_auc":          round(float(average_precision_score(y_test, probas)), 4),
        "mcc":             round(float(matthews_corrcoef(y_test, preds)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }

    print(f"\n[Evaluation] {label}")
    print(f"  Threshold:  {threshold:.3f}")
    print(f"  Precision:  {metrics['precision']:.4f}")
    print(f"  Recall:     {metrics['recall']:.4f}")
    print(f"  F1:         {metrics['f1']:.4f}")
    print(f"  AUC-ROC:    {metrics['auc_roc']:.4f}")
    print(f"  PR-AUC:     {metrics['pr_auc']:.4f}  ← primary metric")
    print(f"  MCC:        {metrics['mcc']:.4f}")
    print(f"  TP: {tp:>5} | FP: {fp:>5}")
    print(f"  FN: {fn:>5} | TN: {tn:>6}")
    print(classification_report(y_test, preds, target_names=["Legitimate", "Fraud"]))
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# STAGE 8 — SHAP Explainer (FIX 3: per-prediction explanations)
# ══════════════════════════════════════════════════════════════════════════════
def build_shap_explainer(model, X_train_s, feature_cols: list[str], model_name: str):
    """
    Build and save a SHAP TreeExplainer.
    Saves: shap_explainer.pkl + shap_feature_importance.json
    """
    if not HAS_SHAP:
        print("[SHAP] Skipped — install shap: pip install shap")
        return None

    print(f"\n[Stage 8] Building SHAP TreeExplainer for {model_name}...")
    t0 = time.time()

    explainer = shap.TreeExplainer(model)

    # Compute SHAP values on a sample of training data (not full set — too slow)
    sample_size = min(2000, len(X_train_s))
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(X_train_s), size=sample_size, replace=False)
    X_sample = X_train_s[idx]

    shap_values = explainer.shap_values(X_sample)
    # For binary classifiers: shap_values may be list [class0, class1]
    if isinstance(shap_values, list):
        shap_vals = shap_values[1]   # fraud class
    else:
        shap_vals = shap_values

    mean_abs_shap = np.abs(shap_vals).mean(axis=0)
    importance = {
        feature_cols[i]: round(float(mean_abs_shap[i]), 6)
        for i in range(len(feature_cols))
    }
    # Sort descending
    importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    # Save
    explainer_path = ARTIFACTS_DIR / f"{model_name}_shap_explainer.pkl"
    importance_path = ARTIFACTS_DIR / f"{model_name}_shap_importance.json"
    joblib.dump(explainer, explainer_path)
    with open(importance_path, "w") as f:
        json.dump(importance, f, indent=2)

    elapsed = time.time() - t0
    print(f"  Computed on {sample_size} samples in {elapsed:.1f}s")
    print(f"  Top 5 features:")
    for feat, val in list(importance.items())[:5]:
        print(f"    {feat:25s}: {val:.4f}")
    print(f"  Saved explainer → {explainer_path.name}")

    return explainer


# ══════════════════════════════════════════════════════════════════════════════
# MODEL A — Logistic Regression (baseline)
# ══════════════════════════════════════════════════════════════════════════════
def train_logistic_regression(X_res, y_res, X_val, y_val, X_test, y_test,
                               X_train_s, feature_cols) -> dict:
    from sklearn.model_selection import GridSearchCV

    print("\n" + "═"*60)
    print("[Model A] Logistic Regression")
    print("═"*60)

    param_grid = {"C": [0.001, 0.01, 0.1, 1.0, 10.0]}
    lr = LogisticRegression(
        solver="saga", class_weight="balanced",
        max_iter=2000, random_state=RANDOM_STATE, n_jobs=-1,
    )
    grid = GridSearchCV(lr, param_grid, cv=5, scoring="average_precision",
                        n_jobs=-1, verbose=0)
    grid.fit(X_res, y_res)
    best_lr = grid.best_estimator_
    print(f"  Best C: {grid.best_params_['C']}")

    # Threshold on validation set
    threshold, val_f1 = optimize_threshold(best_lr, X_val, y_val)
    print(f"  Optimal threshold (val): {threshold:.3f}  (val F1: {val_f1:.4f})")

    # Evaluate on test set
    metrics = evaluate(best_lr, X_test, y_test, threshold, "logistic_regression")
    metrics["best_C"] = grid.best_params_["C"]
    metrics["val_f1"] = round(val_f1, 4)

    # Save
    model_path = ARTIFACTS_DIR / "logistic_regression.pkl"
    meta_path  = ARTIFACTS_DIR / "lr_metadata.json"
    joblib.dump(best_lr, model_path)
    with open(meta_path, "w") as f:
        json.dump({
            **metrics,
            "model_path":  str(model_path),
            "scaler_path": str(ARTIFACTS_DIR / "scaler.pkl"),
        }, f, indent=2)

    print(f"\n  Saved → {model_path.name}")

    # SHAP (LR uses LinearExplainer — faster)
    if HAS_SHAP:
        try:
            explainer = shap.LinearExplainer(best_lr, X_train_s,
                                              feature_perturbation="interventional")
            joblib.dump(explainer, ARTIFACTS_DIR / "logistic_regression_shap_explainer.pkl")
            print(f"  Saved → logistic_regression_shap_explainer.pkl")
        except Exception as e:
            print(f"  [SHAP] LinearExplainer failed: {e}")

    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# MODEL B — XGBoost with Optuna (FIX 3: primary production model)
# ══════════════════════════════════════════════════════════════════════════════
def train_xgboost(X_res, y_res, X_val, y_val, X_test, y_test,
                  X_train_s, feature_cols, use_optuna: bool = True) -> dict:
    if not HAS_XGB:
        print("[Model B] XGBoost not available — skipping")
        return {}

    print("\n" + "═"*60)
    print("[Model B] XGBoost" + (" + Optuna tuning" if use_optuna and HAS_OPTUNA else ""))
    print("═"*60)

    # Class imbalance ratio for scale_pos_weight
    fraud_count = int(y_res.sum()) if y_res.sum() > 0 else 1
    legit_count = len(y_res) - fraud_count
    # After SMOTE they are balanced — use original ratio for XGB
    orig_ratio = round((284315 - 492) / 492)  # ~577

    def train_and_score(params: dict) -> float:
        """Train XGBoost, return PR-AUC on validation set."""
        model = xgb.XGBClassifier(
            **params,
            scale_pos_weight=orig_ratio,
            eval_metric="aucpr",
            use_label_encoder=False,
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbosity=0,
        )
        model.fit(X_res, y_res,
                  eval_set=[(X_val, y_val)],
                  verbose=False)
        probas = model.predict_proba(X_val)[:, 1]
        return average_precision_score(y_val, probas)

    # ── Optuna tuning ─────────────────────────────────────────────────────────
    if use_optuna and HAS_OPTUNA:
        def objective(trial):
            params = {
                "n_estimators":    trial.suggest_int("n_estimators", 200, 800),
                "max_depth":       trial.suggest_int("max_depth", 3, 8),
                "learning_rate":   trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample":       trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree":trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight":trial.suggest_int("min_child_weight", 1, 10),
                "gamma":           trial.suggest_float("gamma", 0, 5),
                "reg_alpha":       trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda":      trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            }
            return train_and_score(params)

        study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=10),
        )
        print(f"  Running Optuna (50 trials, TPE sampler)...")
        study.optimize(objective, n_trials=50, show_progress_bar=False, n_jobs=1)
        best_params = study.best_params
        best_val_prauc = study.best_value
        print(f"  Best PR-AUC (val): {best_val_prauc:.4f}")
        print(f"  Best params: {best_params}")
    else:
        # Sensible defaults when Optuna not available
        best_params = {
            "n_estimators": 500, "max_depth": 6,
            "learning_rate": 0.05, "subsample": 0.8,
            "colsample_bytree": 0.8, "min_child_weight": 5,
            "gamma": 0, "reg_alpha": 0.1, "reg_lambda": 1.0,
        }
        best_val_prauc = 0.0
        print("  Using default params (Optuna not available)")

    # ── Final training with best params ───────────────────────────────────────
    best_xgb = xgb.XGBClassifier(
        **best_params,
        scale_pos_weight=orig_ratio,
        eval_metric="aucpr",
        use_label_encoder=False,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        verbosity=0,
    )
    best_xgb.fit(X_res, y_res, eval_set=[(X_val, y_val)], verbose=False)

    # Threshold on VALIDATION set
    threshold, val_f1 = optimize_threshold(best_xgb, X_val, y_val)
    print(f"  Optimal threshold (val): {threshold:.3f}  (val F1: {val_f1:.4f})")

    # Final evaluation on TEST set
    metrics = evaluate(best_xgb, X_test, y_test, threshold, "xgboost")
    metrics["hyperparams"] = best_params
    metrics["val_prauc"] = round(best_val_prauc, 4)
    metrics["val_f1"]    = round(val_f1, 4)

    # Save
    model_path = ARTIFACTS_DIR / "xgboost.pkl"
    meta_path  = ARTIFACTS_DIR / "xgboost_metadata.json"
    joblib.dump(best_xgb, model_path)
    with open(meta_path, "w") as f:
        json.dump({
            **metrics,
            "model_path":            str(model_path),
            "scaler_path":           str(ARTIFACTS_DIR / "scaler.pkl"),
            "shap_explainer_path":   str(ARTIFACTS_DIR / "xgboost_shap_explainer.pkl"),
            "shap_importance_path":  str(ARTIFACTS_DIR / "xgboost_shap_importance.json"),
            "feature_names":         feature_cols,
        }, f, indent=2, default=str)

    print(f"\n  Saved → {model_path.name}")

    # SHAP TreeExplainer
    build_shap_explainer(best_xgb, X_train_s, feature_cols, "xgboost")

    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# MODEL C — Isolation Forest (unsupervised anomaly baseline)
# ══════════════════════════════════════════════════════════════════════════════
def train_isolation_forest(X_train_s, X_test, y_test) -> dict:
    print("\n" + "═"*60)
    print("[Model C] Isolation Forest (unsupervised baseline)")
    print("═"*60)

    contamination = 492 / 284807
    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    iso.fit(X_train_s)

    # Use anomaly SCORES for ROC-AUC (not binary predictions)
    scores = -iso.score_samples(X_test)   # higher = more anomalous
    auc = roc_auc_score(y_test, scores)
    pr_auc = average_precision_score(y_test, scores)

    # Binary predictions at contamination threshold
    y_pred_raw = iso.predict(X_test)
    y_pred = np.where(y_pred_raw == -1, 1, 0)
    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()

    metrics = {
        "algorithm": "isolation_forest",
        "auc_roc":   round(float(auc), 4),
        "pr_auc":    round(float(pr_auc), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1":        round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "note": "Evaluated using anomaly scores (not binary threshold) for AUC metrics",
    }
    print(f"  AUC-ROC: {metrics['auc_roc']}  |  PR-AUC: {metrics['pr_auc']}")
    print(f"  Precision: {metrics['precision']}  |  Recall: {metrics['recall']}")

    model_path = ARTIFACTS_DIR / "isolation_forest.pkl"
    joblib.dump(iso, model_path)
    print(f"  Saved → {model_path.name}")
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — Orchestration
# ══════════════════════════════════════════════════════════════════════════════
def run_pipeline(model: str = "all", tune: bool = True):
    t_start = time.time()
    print("\n" + "█"*60)
    print("  FraudShield ML Training Pipeline  v2.0")
    print("█"*60)

    # Stage 1 — Load
    df = load_data()

    # Stage 2 — Feature Engineering (FIX 2)
    df, feature_cols = engineer_features(df)

    # Save feature names for inference pipeline
    with open(ARTIFACTS_DIR / "feature_names.json", "w") as f:
        json.dump(feature_cols, f, indent=2)

    # Stage 3 — Chronological Split (FIX 1)
    X_train, X_val, X_test, y_train, y_val, y_test = chronological_split(df, feature_cols)

    # Stage 4 — Scale
    X_train_s, X_val_s, X_test_s, scaler, scale_indices = scale_features(
        X_train, X_val, X_test, feature_cols
    )

    # Save scale indices for inference
    with open(ARTIFACTS_DIR / "scale_indices.json", "w") as f:
        json.dump(scale_indices, f)

    # Stage 5 — SMOTE (on scaled training set only)
    X_res, y_res = apply_smote(X_train_s, y_train)

    results = {}

    # Stage 6 — Train models
    if model in ("lr", "all"):
        results["logistic_regression"] = train_logistic_regression(
            X_res, y_res, X_val_s, y_val, X_test_s, y_test, X_train_s, feature_cols
        )

    if model in ("xgboost", "all"):
        results["xgboost"] = train_xgboost(
            X_res, y_res, X_val_s, y_val, X_test_s, y_test,
            X_train_s, feature_cols, use_optuna=tune
        )

    if model in ("isolation_forest", "all"):
        results["isolation_forest"] = train_isolation_forest(X_train_s, X_test_s, y_test)

    # Save combined summary
    elapsed = time.time() - t_start
    summary = {
        "pipeline_version": "2.0",
        "timestamp": pd.Timestamp.now().isoformat(),
        "split_strategy": "chronological",
        "feature_count": len(feature_cols),
        "smote_applied": True,
        "scaler": "RobustScaler",
        "training_time_seconds": round(elapsed, 1),
        "results": results,
    }
    with open(ARTIFACTS_DIR / "training_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # Final report
    print("\n" + "═"*60)
    print("  TRAINING COMPLETE")
    print("═"*60)
    print(f"  Time elapsed: {elapsed:.0f}s")
    print(f"  Artifacts saved to: {ARTIFACTS_DIR}")
    print()
    for name, m in results.items():
        if m:
            print(f"  {name:25s}  PR-AUC: {m.get('pr_auc','—')}  "
                  f"Recall: {m.get('recall','—')}  F1: {m.get('f1','—')}")
    print()

    # Recommend best model
    if "xgboost" in results and results["xgboost"]:
        best = "xgboost"
    elif "logistic_regression" in results and results["logistic_regression"]:
        best = "logistic_regression"
    else:
        best = None

    if best:
        print(f"  ✓ Recommended model: {best}")
        print(f"    → Run 'make seed' then activate v2.0.0 on /models page")
    print()

    return summary


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FraudShield Training Pipeline v2")
    parser.add_argument("--model", default="all",
                        choices=["lr", "xgboost", "isolation_forest", "all"],
                        help="Which model(s) to train")
    parser.add_argument("--tune", action="store_true", default=True,
                        help="Use Optuna for XGBoost hyperparameter tuning")
    parser.add_argument("--no-tune", dest="tune", action="store_false",
                        help="Skip Optuna — use default XGBoost params (faster)")
    args = parser.parse_args()
    run_pipeline(model=args.model, tune=args.tune)
