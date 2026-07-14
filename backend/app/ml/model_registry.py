"""
ModelRegistry — Production inference engine
Handles: feature engineering, scaling, prediction, SHAP explanation
"""
import json
import time
import joblib
import numpy as np
from typing import Optional, Tuple
from pathlib import Path
from app.core.config import settings

# Optional SHAP
try:
    import shap as shap_lib
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


class ModelRegistry:
    """
    Singleton registry that holds the active ML model in memory.

    Inference pipeline (per transaction):
      raw features → feature engineering → selective scaling → predict_proba
      → apply threshold → SHAP explanation (top 5) → return result
    """

    _instance: Optional["ModelRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.model            = None
        self.scaler           = None
        self.shap_explainer   = None
        self.feature_names: list[str] = []
        self.scale_indices: list[int] = []
        self.active_version_tag: Optional[str] = None
        self.active_version_id:  Optional[str] = None
        self.threshold: float = settings.DEFAULT_THRESHOLD
        self.model_name: str  = "unknown"
        self._initialized = True

    # ── Loading ───────────────────────────────────────────────────────────────
    def load(self, model_path: str, scaler_path: str,
             version_tag: str, version_id: str,
             shap_explainer_path: Optional[str] = None,
             feature_names: Optional[list] = None,
             scale_indices: Optional[list] = None) -> None:
        """Load model + scaler (+ optionally SHAP explainer) from disk."""
        self.model  = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.active_version_tag = version_tag
        self.active_version_id  = version_id
        self.model_name = Path(model_path).stem

        # Feature names — load from artifacts if not provided
        if feature_names:
            self.feature_names = feature_names
        else:
            fn_path = Path(model_path).parent / "feature_names.json"
            if fn_path.exists():
                with open(fn_path) as f:
                    self.feature_names = json.load(f)

        # Scale indices — which feature positions to scale
        if scale_indices:
            self.scale_indices = scale_indices
        else:
            si_path = Path(model_path).parent / "scale_indices.json"
            if si_path.exists():
                with open(si_path) as f:
                    self.scale_indices = json.load(f)

        # SHAP explainer (optional)
        if shap_explainer_path and Path(shap_explainer_path).exists():
            try:
                self.shap_explainer = joblib.load(shap_explainer_path)
                print(f"[ModelRegistry] SHAP explainer loaded")
            except Exception as e:
                print(f"[ModelRegistry] SHAP load failed: {e}")
                self.shap_explainer = None
        else:
            # Auto-detect
            auto_path = Path(model_path).parent / f"{self.model_name}_shap_explainer.pkl"
            if auto_path.exists():
                try:
                    self.shap_explainer = joblib.load(auto_path)
                    print(f"[ModelRegistry] SHAP explainer auto-loaded")
                except Exception:
                    self.shap_explainer = None

        print(f"[ModelRegistry] Loaded {version_tag} ({self.model_name})")
        print(f"  Features: {len(self.feature_names)} | SHAP: {'✓' if self.shap_explainer else '✗'}")

    def is_loaded(self) -> bool:
        return self.model is not None and self.scaler is not None

    # ── Feature Engineering (mirrors train.py Stage 2) ────────────────────────
    def _engineer_features(self, time_seconds: float, amount: float,
                            v_features: list[float]) -> np.ndarray:
        """
        Apply the same feature engineering as the training pipeline.
        Input: time_seconds, amount, v1..v28 (30 raw values)
        Output: numpy array with all engineered features
        """
        import math

        log_amount       = math.log1p(amount)
        is_small_amount  = int(amount < 10)
        is_round_amount  = int(amount % 10 == 0)
        is_large_amount  = int(amount > 1000)

        hour       = int(time_seconds % 86400 // 3600)
        is_night   = int(hour in [0, 1, 2, 3, 4, 5])
        hour_sin   = math.sin(2 * math.pi * hour / 24)
        hour_cos   = math.cos(2 * math.pi * hour / 24)

        if hour < 6:    day_period = 0
        elif hour < 12: day_period = 1
        elif hour < 18: day_period = 2
        else:           day_period = 3

        # Order must match feature_cols in train.py:
        # ["Time", "Amount", V1..V28,
        #  "log_amount", "is_small_amount", "is_round_amount", "is_large_amount",
        #  "hour", "is_night", "hour_sin", "hour_cos", "day_period"]
        raw = [time_seconds, amount] + v_features + [
            log_amount, is_small_amount, is_round_amount, is_large_amount,
            hour, is_night, hour_sin, hour_cos, day_period,
        ]
        return np.array(raw, dtype=float)

    def _scale(self, arr: np.ndarray) -> np.ndarray:
        """Apply RobustScaler to the indices that were scaled during training."""
        scaled = arr.copy()
        if self.scale_indices and self.scaler is not None:
            scaled[self.scale_indices] = self.scaler.transform(
                arr[self.scale_indices].reshape(1, -1)
            ).flatten()
        else:
            # Fallback: scale first 2 features (legacy compatibility)
            scaled[:2] = self.scaler.transform(arr[:2].reshape(1, -1)).flatten()
        return scaled

    # ── SHAP Explanation ──────────────────────────────────────────────────────
    def explain(self, scaled_arr: np.ndarray,
                top_n: int = 5) -> Optional[list[dict]]:
        """
        Compute SHAP values for a single transaction.
        Returns top_n features with their contribution.
        """
        if not self.shap_explainer or not HAS_SHAP:
            return None
        try:
            sv = self.shap_explainer.shap_values(scaled_arr.reshape(1, -1))
            # For binary classifiers, sv may be list [class0, class1]
            if isinstance(sv, list):
                sv = sv[1]
            sv = sv.flatten()

            names = self.feature_names if self.feature_names else [f"f{i}" for i in range(len(sv))]
            pairs = sorted(zip(names, sv), key=lambda x: abs(x[1]), reverse=True)

            return [
                {
                    "feature":   name,
                    "value":     round(float(scaled_arr[names.index(name)] if names.index(name) < len(scaled_arr) else 0), 4),
                    "shap_value": round(float(shap_val), 4),
                    "direction": "fraud" if shap_val > 0 else "legitimate",
                }
                for name, shap_val in pairs[:top_n]
            ]
        except Exception as e:
            print(f"[SHAP] explain() failed: {e}")
            return None

    # ── Single prediction ─────────────────────────────────────────────────────
    def predict(self, time_seconds: float, amount: float,
                v_features: list[float]) -> Tuple[int, float, Optional[list]]:
        """
        Full inference pipeline for one transaction.

        Returns: (predicted_label, fraud_probability, shap_explanation)
        shap_explanation is list of top-5 feature dicts, or None if SHAP unavailable.
        """
        if not self.is_loaded():
            raise RuntimeError("No model loaded. Please activate a model version.")

        # 1. Feature engineering
        arr = self._engineer_features(time_seconds, amount, v_features)

        # 2. Scale
        scaled = self._scale(arr)

        # 3. Predict
        proba = self.model.predict_proba(scaled.reshape(1, -1))[0][1]
        label = int(proba >= self.threshold)

        # 4. SHAP
        explanation = self.explain(scaled)

        return label, float(proba), explanation

    # ── Batch prediction (for Celery) ─────────────────────────────────────────
    def predict_batch(self, rows: list[dict]) -> Tuple[list, list]:
        """
        Batch predict.
        rows: list of {"time_seconds": float, "amount": float, "v_features": [28 floats]}
        Returns: (labels, probabilities)
        """
        if not self.is_loaded():
            raise RuntimeError("No model loaded.")

        arrays = []
        for row in rows:
            arr = self._engineer_features(
                row["time_seconds"], row["amount"], row["v_features"]
            )
            scaled = self._scale(arr)
            arrays.append(scaled)

        matrix = np.array(arrays)
        probas = self.model.predict_proba(matrix)[:, 1]
        labels = (probas >= self.threshold).astype(int).tolist()
        return labels, probas.tolist()

    # ── Legacy compatibility (used by old predict_batch in tasks.py) ──────────
    def predict_batch_raw(self, features_matrix: list) -> Tuple[list, list]:
        """
        Legacy batch predict using raw feature lists [time, amount, v1..v28].
        """
        rows = []
        for feat_list in features_matrix:
            rows.append({
                "time_seconds": feat_list[0],
                "amount":       feat_list[1],
                "v_features":   feat_list[2:30],
            })
        return self.predict_batch(rows)


# Global singleton
model_registry = ModelRegistry()

def get_model_registry() -> ModelRegistry:
    return model_registry
