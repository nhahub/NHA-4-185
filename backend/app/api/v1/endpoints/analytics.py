from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timezone, date
import redis.asyncio as aioredis

from app.db.session import get_db
from app.api.deps import get_current_user, get_redis, get_registry
from app.schemas.schemas import DashboardStats, HealthStatus, ModelVersionOut
from app.models.models import Transaction, Prediction, FraudAlert, AlertStatus, ModelVersion, User
from app.ml.model_registry import ModelRegistry
from app.core.config import settings

router = APIRouter(tags=["Analytics & Health"])


@router.get("/health", response_model=HealthStatus)
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
    registry: ModelRegistry = Depends(get_registry),
):
    # DB check
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Redis check
    redis_status = "ok"
    try:
        await redis.ping()
    except Exception:
        redis_status = "error"

    ml_status = "loaded" if registry.is_loaded() else "no model"
    overall   = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    shap_ok   = registry.is_loaded() and registry.shap_explainer is not None

    return HealthStatus(
        status=overall,
        database=db_status,
        redis=redis_status,
        ml_model=ml_status,
        shap_loaded=shap_ok,
        version=settings.VERSION,
    )


@router.get("/analytics/dashboard", response_model=DashboardStats)
async def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
):
    today = date.today()

    total_tx = (await db.execute(select(func.count()).select_from(Transaction))).scalar()
    total_fraud = (await db.execute(
        select(func.count()).select_from(Prediction).where(Prediction.predicted_label == 1)
    )).scalar()
    open_alerts = (await db.execute(
        select(func.count()).select_from(FraudAlert).where(FraudAlert.status == AlertStatus.open)
    )).scalar()
    today_tx = (await db.execute(
        select(func.count()).select_from(Transaction)
        .where(func.date(Transaction.created_at) == today)
    )).scalar()
    today_fraud = (await db.execute(
        select(func.count()).select_from(Prediction)
        .where(Prediction.predicted_label == 1)
        .where(func.date(Prediction.predicted_at) == today)
    )).scalar()

    # Active model metrics
    active = (await db.execute(
        select(ModelVersion).where(ModelVersion.is_active == True)
    )).scalar_one_or_none()

    # Pull PR-AUC and MCC from hyperparams JSONB (stored by v2 pipeline)
    pr_auc = None
    mcc    = None
    if active and active.hyperparams:
        pr_auc = active.hyperparams.get("pr_auc")
        mcc    = active.hyperparams.get("mcc")

    return DashboardStats(
        total_transactions=total_tx or 0,
        total_fraud=total_fraud or 0,
        fraud_rate=round((total_fraud or 0) / max(total_tx, 1), 4),
        precision=active.precision_score if active else None,
        recall=active.recall_score if active else None,
        auc_roc=active.auc_roc if active else None,
        pr_auc=pr_auc,
        mcc=mcc,
        open_alerts=open_alerts or 0,
        today_transactions=today_tx or 0,
        today_fraud=today_fraud or 0,
    )


@router.get("/models", response_model=list[ModelVersionOut])
async def list_models(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelVersion).order_by(ModelVersion.trained_at.desc()))
    return result.scalars().all()


@router.post("/models/{model_id}/activate", response_model=ModelVersionOut)
async def activate_model(
    model_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
):
    from uuid import UUID
    result = await db.execute(select(ModelVersion).where(ModelVersion.id == UUID(model_id)))
    mv = result.scalar_one_or_none()
    if not mv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Model version not found")

    # Deactivate all
    all_mv = (await db.execute(select(ModelVersion))).scalars().all()
    for m in all_mv:
        m.is_active = False
    mv.is_active = True
    await db.flush()

    # Load into registry
    scaler_path = (mv.hyperparams or {}).get("scaler_path", str(Path(mv.artifact_path).parent / "scaler.pkl"))
    shap_path = (mv.hyperparams or {}).get("shap_explainer_path")
    feature_names = None
    scale_indices = None
    import json as _json
    from pathlib import Path
    artifacts_dir = Path(mv.artifact_path).parent
    fn_path = artifacts_dir / "feature_names.json"
    si_path = artifacts_dir / "scale_indices.json"
    if fn_path.exists():
        with open(fn_path) as f:
            feature_names = _json.load(f)
    if si_path.exists():
        with open(si_path) as f:
            scale_indices = _json.load(f)
    registry.load(
        mv.artifact_path, scaler_path,
        mv.version_tag, str(mv.id),
        shap_explainer_path=shap_path,
        feature_names=feature_names,
        scale_indices=scale_indices,
    )
    return mv


# ── Phase 2: Live analytics endpoints ────────────────────────────────────────

@router.get("/analytics/trend")
async def fraud_trend(
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily transaction + fraud counts for the last N days."""
    result = await db.execute(
        text("""
            SELECT
                DATE(t.created_at)  AS day,
                COUNT(t.id)          AS total,
                COALESCE(SUM(CASE WHEN p.predicted_label = 1 THEN 1 ELSE 0 END), 0) AS fraud
            FROM transactions t
            LEFT JOIN predictions p ON p.transaction_id = t.id
            WHERE t.created_at >= NOW() - (CAST(:days AS INT) * INTERVAL '1 day')
            GROUP BY DATE(t.created_at)
            ORDER BY day ASC
        """).bindparams(days=days)
    )
    rows = result.fetchall()
    return [
        {
            "day": str(r.day),
            "total": int(r.total),
            "fraud": int(r.fraud),
            "fraud_rate": round(r.fraud / r.total, 4) if r.total else 0,
        }
        for r in rows
    ]


@router.get("/analytics/confusion-matrix")
async def confusion_matrix_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """TP/TN/FP/FN from predictions where true_label is known."""
    result = await db.execute(text("""
        SELECT
            SUM(CASE WHEN p.predicted_label=0 AND t.true_label=0 THEN 1 ELSE 0 END) AS tn,
            SUM(CASE WHEN p.predicted_label=1 AND t.true_label=0 THEN 1 ELSE 0 END) AS fp,
            SUM(CASE WHEN p.predicted_label=0 AND t.true_label=1 THEN 1 ELSE 0 END) AS fn,
            SUM(CASE WHEN p.predicted_label=1 AND t.true_label=1 THEN 1 ELSE 0 END) AS tp,
            COUNT(*) AS total
        FROM predictions p
        JOIN transactions t ON t.id = p.transaction_id
        WHERE t.true_label IS NOT NULL
    """))
    row = result.fetchone()
    if not row or not row.total:
        return {"tn": 0, "fp": 0, "fn": 0, "tp": 0, "total": 0, "precision": None, "recall": None, "accuracy": None}
    tn, fp, fn, tp = int(row.tn or 0), int(row.fp or 0), int(row.fn or 0), int(row.tp or 0)
    total = tn + fp + fn + tp
    return {
        "tn": tn, "fp": fp, "fn": fn, "tp": tp, "total": total,
        "precision": round(tp / (tp + fp), 4) if (tp + fp) > 0 else None,
        "recall":    round(tp / (tp + fn), 4) if (tp + fn) > 0 else None,
        "accuracy":  round((tp + tn) / total, 4) if total > 0 else None,
    }


@router.get("/analytics/fraud-by-amount")
async def fraud_by_amount(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fraud count bucketed by transaction amount ranges."""
    result = await db.execute(text("""
        SELECT
            CASE
                WHEN t.amount <   10 THEN '< $10'
                WHEN t.amount <   50 THEN '$10-49'
                WHEN t.amount <  100 THEN '$50-99'
                WHEN t.amount <  500 THEN '$100-499'
                WHEN t.amount < 1000 THEN '$500-999'
                ELSE '$1000+'
            END AS bucket,
            COUNT(*) AS total,
            SUM(CASE WHEN p.predicted_label = 1 THEN 1 ELSE 0 END) AS fraud
        FROM transactions t
        LEFT JOIN predictions p ON p.transaction_id = t.id
        GROUP BY bucket
        ORDER BY MIN(t.amount)
    """))
    rows = result.fetchall()
    return [
        {
            "bucket": r.bucket,
            "total": int(r.total),
            "fraud": int(r.fraud or 0),
            "fraud_rate": round((r.fraud or 0) / r.total, 4) if r.total else 0,
        }
        for r in rows
    ]


@router.get("/analytics/top-alerts")
async def top_alerts(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Most critical open alerts ordered by fraud probability."""
    result = await db.execute(
        select(FraudAlert, Prediction)
        .join(Prediction, Prediction.id == FraudAlert.prediction_id)
        .where(FraudAlert.status == "open")
        .order_by(Prediction.fraud_probability.desc())
        .limit(limit)
    )
    rows = result.fetchall()
    return [
        {
            "alert_id":          str(alert.id),
            "severity":          alert.severity,
            "status":            alert.status,
            "fraud_probability": pred.fraud_probability,
            "created_at":        alert.created_at.isoformat(),
        }
        for alert, pred in rows
    ]


@router.post("/models/threshold")
async def update_threshold(
    threshold: float = Query(..., ge=0.01, le=0.99),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    registry: ModelRegistry = Depends(get_registry),
):
    """Update the decision threshold for the active model."""
    if not registry.is_loaded():
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="No active model loaded")
    registry.threshold = threshold

    # Persist on the active model_version row
    result = await db.execute(select(ModelVersion).where(ModelVersion.is_active == True))
    mv = result.scalar_one_or_none()
    if mv:
        mv.hyperparams = {**(mv.hyperparams or {}), "threshold": threshold}
        await db.flush()

    return {"threshold": threshold, "model_version": registry.active_version_tag}
