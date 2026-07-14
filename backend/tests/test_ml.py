import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from app.ml.model_registry import ModelRegistry


def test_model_registry_singleton():
    r1 = ModelRegistry()
    r2 = ModelRegistry()
    assert r1 is r2


def test_model_registry_not_loaded():
    registry = ModelRegistry()
    registry.model = None
    registry.scaler = None
    assert not registry.is_loaded()


def test_model_registry_predict_not_loaded():
    registry = ModelRegistry()
    registry.model = None
    with pytest.raises(RuntimeError, match="No model loaded"):
        registry.predict(0.0, 1.0, [0.0] * 28)


def _setup_mock_registry(threshold=0.5, proba_value=0.12):
    """Helper to set up a mock registry for prediction tests."""
    registry = ModelRegistry()
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[1 - proba_value, proba_value]])

    mock_scaler = MagicMock()
    mock_scaler.transform.return_value = np.zeros((1, 2))

    registry.model = mock_model
    registry.scaler = mock_scaler
    registry.threshold = threshold
    registry.active_version_tag = "v1.0.0"
    registry.active_version_id = "00000000-0000-0000-0000-000000000001"
    registry.feature_names = [f"f{i}" for i in range(39)]
    registry.scale_indices = [0, 1]
    return registry, mock_model


def test_model_registry_predict_loaded():
    registry, _ = _setup_mock_registry(threshold=0.5, proba_value=0.12)
    label, prob, explanation = registry.predict(0.0, 1.0, [0.0] * 28)
    assert label == 0        # prob=0.12 < threshold=0.5
    assert abs(prob - 0.12) < 1e-6


def test_model_registry_fraud_prediction():
    registry, _ = _setup_mock_registry(threshold=0.5, proba_value=0.95)
    label, prob, explanation = registry.predict(0.0, 1.0, [0.0] * 28)
    assert label == 1        # fraud
    assert prob > 0.5


def test_batch_predict_shape():
    registry, mock_model = _setup_mock_registry(threshold=0.5, proba_value=0.5)
    mock_model.predict_proba.return_value = np.array([[0.9, 0.1], [0.2, 0.8], [0.7, 0.3]])

    mock_scaler = MagicMock()
    mock_scaler.transform.return_value = np.zeros((3, 2))
    registry.scaler = mock_scaler

    rows = [{"time_seconds": 0.0, "amount": 1.0, "v_features": [0.0] * 28} for _ in range(3)]
    labels, probas = registry.predict_batch(rows)
    assert len(labels) == 3
    assert len(probas) == 3
    assert labels[0] == 0   # 0.1 < 0.5
    assert labels[1] == 1   # 0.8 > 0.5
