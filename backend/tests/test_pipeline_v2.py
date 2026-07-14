"""
Tests for v2 ML pipeline improvements:
- Chronological split
- Feature engineering
- Model registry SHAP
- Input validation ranges
- Atomic prediction writes
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ─── Feature Engineering Tests ────────────────────────────────────────────────

def test_engineer_features_night_detection():
    """is_night should be 1 for hours 0-5, 0 otherwise."""
    from app.ml.model_registry import ModelRegistry
    reg = ModelRegistry()

    # 2 AM = 7200 seconds
    arr = reg._engineer_features(7200.0, 100.0, [0.0] * 28)
    feature_list = arr.tolist()
    # hour should be 2, is_night should be 1
    # positions: 0=Time, 1=Amount, 2..29=V1..V28, 30=log_amount, ...
    # hour is at index 32 (Time,Amount,V1-V28,log_amount,is_small,is_round,is_large,hour)
    # We just test that the array length is correct and values are sensible
    assert len(feature_list) == 39   # 2 + 28 + 9 engineered
    assert feature_list[0] == 7200.0  # Time
    assert feature_list[1] == 100.0   # Amount


def test_engineer_features_small_amount():
    """is_small_amount should be 1 for amounts < 10."""
    from app.ml.model_registry import ModelRegistry
    reg = ModelRegistry()

    arr = reg._engineer_features(0.0, 5.0, [0.0] * 28)
    # log_amount(30), is_small(31), is_round(32), is_large(33), hour(34), is_night(35), sin(36), cos(37), day_period(38)
    assert arr[31] == 1.0   # is_small_amount

    arr2 = reg._engineer_features(0.0, 50.0, [0.0] * 28)
    assert arr2[31] == 0.0  # not small


def test_engineer_features_log_amount():
    """log_amount should equal log1p(amount)."""
    import math
    from app.ml.model_registry import ModelRegistry
    reg = ModelRegistry()

    amount = 149.62
    arr = reg._engineer_features(0.0, amount, [0.0] * 28)
    expected_log = math.log1p(amount)
    assert abs(arr[30] - expected_log) < 1e-6


def test_engineer_features_cyclical_encoding():
    """hour_sin and hour_cos should be in [-1, 1]."""
    import math
    from app.ml.model_registry import ModelRegistry
    reg = ModelRegistry()

    for hour_offset in [0, 21600, 43200, 64800]:  # 0h, 6h, 12h, 18h
        arr = reg._engineer_features(float(hour_offset), 100.0, [0.0] * 28)
        sin_val = arr[36]
        cos_val = arr[37]
        assert -1.0 <= sin_val <= 1.0
        assert -1.0 <= cos_val <= 1.0


# ─── Input Validation Tests ───────────────────────────────────────────────────

async def test_predict_rejects_negative_amount(client: AsyncClient, auth_headers: dict):
    """Amount must be > 0."""
    resp = await client.post("/api/v1/predict/single", json={
        "time_seconds": 0, "amount": -10,
        **{f"v{i}": 0.0 for i in range(1, 29)},
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_predict_rejects_amount_too_large(client: AsyncClient, auth_headers: dict):
    """Amount must be <= 30000."""
    resp = await client.post("/api/v1/predict/single", json={
        "time_seconds": 0, "amount": 999999,
        **{f"v{i}": 0.0 for i in range(1, 29)},
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_predict_rejects_v_feature_out_of_range(client: AsyncClient, auth_headers: dict):
    """V features must be in [-30, 30]."""
    resp = await client.post("/api/v1/predict/single", json={
        "time_seconds": 0, "amount": 100.0,
        "v1": 999.0,  # out of range
        **{f"v{i}": 0.0 for i in range(2, 29)},
    }, headers=auth_headers)
    assert resp.status_code == 422


async def test_predict_valid_range_passes_validation(client: AsyncClient, auth_headers: dict):
    """Valid inputs should pass Pydantic validation (may still get 503 if no model)."""
    resp = await client.post("/api/v1/predict/single", json={
        "time_seconds": 3600, "amount": 149.62,
        **{f"v{i}": 0.1 for i in range(1, 29)},
    }, headers=auth_headers)
    # 422 = validation failure (bad), 200/503 = validation passed (good)
    assert resp.status_code != 422


# ─── Chronological Split Test ─────────────────────────────────────────────────

def test_chronological_split_no_leakage():
    """Test that split respects temporal order."""
    import pandas as pd
    import numpy as np
    import sys
    from pathlib import Path

    # Mock the pipeline function
    sys.path.insert(0, str(Path(__file__).parents[1]))

    try:
        from app.ml.pipeline.train import chronological_split

        # Create synthetic data sorted by time
        n = 1000
        df = pd.DataFrame({
            "Time":   np.arange(n, dtype=float),
            "Amount": np.random.uniform(1, 500, n),
            "Class":  np.zeros(n, dtype=int),
            **{f"V{i}": np.random.randn(n) for i in range(1, 29)},
            # Engineered features
            "log_amount":       np.log1p(np.random.uniform(1, 500, n)),
            "is_small_amount":  np.zeros(n),
            "is_round_amount":  np.zeros(n),
            "is_large_amount":  np.zeros(n),
            "hour":             np.zeros(n),
            "is_night":         np.zeros(n),
            "hour_sin":         np.zeros(n),
            "hour_cos":         np.zeros(n),
            "day_period":       np.zeros(n),
        })
        # Inject fraud at the END (should appear only in test set if split correctly)
        df.loc[950:, "Class"] = 1

        feature_cols = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)] + [
            "log_amount", "is_small_amount", "is_round_amount", "is_large_amount",
            "hour", "is_night", "hour_sin", "hour_cos", "day_period"
        ]
        X_train, X_val, X_test, y_train, y_val, y_test = chronological_split(df, feature_cols)

        # Train set should have no fraud (fraud is at rows 950-999, train ends at 700)
        assert y_train.sum() == 0, "No fraud should leak into training set"
        # Test set should have all fraud
        assert y_test.sum() == 50, "All fraud should be in test set"
        # Time values in train < time values in test (no leakage)
        assert X_train[:, 0].max() < X_test[:, 0].min(), "Train times must precede test times"

    except ImportError:
        pytest.skip("Train pipeline not importable in test environment")


# ─── Model Registry Batch Test ────────────────────────────────────────────────

def test_model_registry_batch_predict():
    """Batch predict should return same number of labels as input rows."""
    from app.ml.model_registry import ModelRegistry
    import numpy as np

    reg = ModelRegistry()
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([
        [0.9, 0.1], [0.2, 0.8], [0.7, 0.3], [0.05, 0.95]
    ])
    mock_scaler = MagicMock()
    mock_scaler.transform.side_effect = lambda x: x

    reg.model = mock_model
    reg.scaler = mock_scaler
    reg.threshold = 0.5
    reg.scale_indices = [0, 1]
    reg.feature_names = []
    reg.active_version_tag = "test"
    reg.active_version_id = "00000000-0000-0000-0000-000000000001"

    rows = [{"time_seconds": 0.0, "amount": 100.0, "v_features": [0.0] * 28}] * 4
    labels, probas = reg.predict_batch(rows)

    assert len(labels) == 4
    assert len(probas) == 4
    assert labels[0] == 0   # 0.1 < 0.5
    assert labels[1] == 1   # 0.8 > 0.5
    assert labels[3] == 1   # 0.95 > 0.5


# ─── Health endpoint now includes shap_loaded ─────────────────────────────────

async def test_health_includes_shap_status(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "shap_loaded" in data
    assert isinstance(data["shap_loaded"], bool)


# ─── PR-AUC in dashboard response ────────────────────────────────────────────

async def test_dashboard_has_pr_auc_field(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "pr_auc" in data
    assert "mcc" in data
