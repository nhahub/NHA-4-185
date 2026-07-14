"""
PredictionService — Single and batch inference with SHAP explanations.
All DB writes are wrapped in one atomic flush to prevent orphaned records.
"""
import time
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Transaction, Prediction, FraudAlert, AlertSeverity, AlertStatus
from app.schemas.schemas import TransactionCreate, PredictionResult
from app.ml.model_registry import ModelRegistry
from fastapi import HTTPException


def _severity_from_prob(prob: float) -> AlertSeverity:
    if prob >= 0.95:  return AlertSeverity.critical
    if prob >= 0.80:  return AlertSeverity.high
    if prob >= 0.60:  return AlertSeverity.medium
    return AlertSeverity.low


class PredictionService:
    def __init__(self, db: AsyncSession, registry: ModelRegistry):
        self.db = db
        self.registry = registry

    async def predict_single(self, data: TransactionCreate, user_id: UUID) -> PredictionResult:
        if not self.registry.is_loaded():
            raise HTTPException(
                status_code=503,
                detail="ML model not loaded. Activate a model version on /models page."
            )

        v_features = [getattr(data, f"v{i}") for i in range(1, 29)]

        # ── Inference (before any DB writes — FIX atomicity) ─────────────────
        t0 = time.perf_counter()
        label, prob, shap_explanation = self.registry.predict(
            time_seconds=data.time_seconds,
            amount=data.amount,
            v_features=v_features,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        # ── All DB writes in one atomic block ─────────────────────────────────
        # FIX: if prediction fails, no orphaned transaction record is created
        try:
            tx = Transaction(
                time_seconds=data.time_seconds,
                amount=data.amount,
                v_features=v_features,
                source="api",
                uploaded_by=user_id,
            )
            self.db.add(tx)
            await self.db.flush()   # get tx.id

            pred = Prediction(
                transaction_id=tx.id,
                model_version_id=UUID(self.registry.active_version_id),
                predicted_label=label,
                fraud_probability=prob,
                decision_threshold=self.registry.threshold,
                latency_ms=round(latency_ms, 2),
            )
            self.db.add(pred)
            await self.db.flush()   # get pred.id

            alert_id = None
            if label == 1:
                alert = FraudAlert(
                    prediction_id=pred.id,
                    severity=_severity_from_prob(prob),
                    status=AlertStatus.open,
                )
                self.db.add(alert)
                await self.db.flush()
                alert_id = alert.id

        except Exception as exc:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail=f"DB write failed: {exc}") from exc

        return PredictionResult(
            prediction_id=pred.id,
            transaction_id=tx.id,
            predicted_label=label,
            fraud_probability=prob,
            decision_threshold=self.registry.threshold,
            is_fraud=bool(label),
            alert_id=alert_id,
            latency_ms=round(latency_ms, 2),
            model_version=self.registry.active_version_tag or "unknown",
            shap_explanation=shap_explanation,
        )
