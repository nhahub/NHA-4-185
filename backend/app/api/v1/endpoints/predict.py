"""
Prediction endpoints — single + batch.
Response now includes SHAP explanation when available.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db
from app.api.deps import get_current_user, get_registry
from app.schemas.schemas import TransactionCreate, PredictionResult, BatchJobStatus, ShapFeature
from app.services.prediction_service import PredictionService
from app.services.tasks import batch_predict_task
from app.ml.model_registry import ModelRegistry
from app.models.models import User, Prediction
from app.core.rate_limit import limiter
from sqlalchemy import select
from uuid import UUID
from celery.result import AsyncResult

router = APIRouter(prefix="/predict", tags=["Predictions"])


@router.post("/single", response_model=PredictionResult)
async def predict_single(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
):
    """
    Predict a single transaction.
    Returns: label, probability, SHAP explanation (top 5 features), alert_id if fraud.
    """
    svc = PredictionService(db, registry)
    return await svc.predict_single(data, current_user.id)


@router.post("/batch", response_model=BatchJobStatus, status_code=202)
@limiter.limit("5/minute")
async def predict_batch(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    registry: ModelRegistry = Depends(get_registry),
):
    """Upload CSV for async batch prediction. Returns job_id to poll."""
    if not registry.is_loaded():
        raise HTTPException(status_code=503, detail="No active ML model loaded")
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")

    contents = await file.read()
    if len(contents) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100 MB)")

    task = batch_predict_task.delay(contents.decode("utf-8"), str(current_user.id))
    return BatchJobStatus(job_id=task.id, status="pending")


@router.get("/batch/{job_id}", response_model=BatchJobStatus)
async def batch_status(job_id: str):
    """Poll status of a batch prediction job."""
    result = AsyncResult(job_id)
    if result.state == "PENDING":
        return BatchJobStatus(job_id=job_id, status="pending")
    elif result.state == "STARTED":
        meta = result.info or {}
        return BatchJobStatus(job_id=job_id, status="started",
                              processed=meta.get("processed"),
                              total=meta.get("total"))
    elif result.state == "SUCCESS":
        info = result.result or {}
        app_status = info.get("status", "completed")
        return BatchJobStatus(
            job_id=job_id,
            status="failed" if app_status == "failed" else "completed",
            total=info.get("total"),
            processed=info.get("total"),
            fraud_count=info.get("fraud_count"),
        )
    else:
        return BatchJobStatus(job_id=job_id, status="failed")


@router.get("/{prediction_id}/explain")
async def explain_prediction(
    prediction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
):
    """
    Compute SHAP explanation for a stored prediction.
    Re-runs inference on the stored transaction features.
    """
    from app.models.models import Transaction

    # Fetch prediction + transaction
    result = await db.execute(
        select(Prediction).where(Prediction.id == prediction_id)
    )
    pred = result.scalar_one_or_none()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")

    result = await db.execute(
        select(Transaction).where(Transaction.id == pred.transaction_id)
    )
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if not registry.is_loaded():
        raise HTTPException(status_code=503, detail="Model not loaded")

    # Re-run inference to get SHAP
    _, _, explanation = registry.predict(
        time_seconds=tx.time_seconds,
        amount=float(tx.amount),
        v_features=tx.v_features,
    )

    if not explanation:
        raise HTTPException(
            status_code=501,
            detail="SHAP explainer not available. Train model with: python -m app.ml.pipeline.train"
        )

    return {
        "prediction_id":    str(prediction_id),
        "predicted_label":  pred.predicted_label,
        "fraud_probability": pred.fraud_probability,
        "explanation":      explanation,
        "model_version":    registry.active_version_tag,
    }
