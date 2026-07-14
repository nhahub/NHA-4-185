from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from typing import List
from datetime import date, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.models import Transaction, Prediction, User

router = APIRouter(prefix="/analytics", tags=["Analytics - Trends"])


class TrendPoint(BaseModel):
    label: str
    transactions: int
    fraud: int
    fraud_rate: float


@router.get("/trend", response_model=List[TrendPoint])
async def get_trend(
    days: int = Query(7, ge=1, le=90, description="Number of past days to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return daily transaction count + fraud count for the last N days.
    Used for the dashboard trend chart.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    # Daily transaction counts
    tx_q = (
        select(
            cast(Transaction.created_at, Date).label("day"),
            func.count(Transaction.id).label("tx_count"),
        )
        .where(cast(Transaction.created_at, Date) >= start_date)
        .group_by(cast(Transaction.created_at, Date))
    )
    tx_result = await db.execute(tx_q)
    tx_by_day: dict[date, int] = {row.day: row.tx_count for row in tx_result}

    # Daily fraud counts (predicted_label = 1)
    fraud_q = (
        select(
            cast(Prediction.predicted_at, Date).label("day"),
            func.count(Prediction.id).label("fraud_count"),
        )
        .where(Prediction.predicted_label == 1)
        .where(cast(Prediction.predicted_at, Date) >= start_date)
        .group_by(cast(Prediction.predicted_at, Date))
    )
    fraud_result = await db.execute(fraud_q)
    fraud_by_day: dict[date, int] = {row.day: row.fraud_count for row in fraud_result}

    # Build a point for every day in the range (fill 0 for missing days)
    trend: List[TrendPoint] = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        tx_count    = tx_by_day.get(day, 0)
        fraud_count = fraud_by_day.get(day, 0)
        trend.append(TrendPoint(
            label=day.strftime("%a %d"),
            transactions=tx_count,
            fraud=fraud_count,
            fraud_rate=round(fraud_count / max(tx_count, 1), 4),
        ))

    return trend


@router.get("/confusion-matrix")
async def get_confusion_matrix(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return TP/TN/FP/FN counts for the active model using is_correct field.
    Only includes predictions where true_label (ground truth) is known.
    """
    # Subquery: join predictions with transactions that have true_label
    from sqlalchemy import case
    from app.models.models import ModelVersion

    active_mv = (await db.execute(
        select(ModelVersion).where(ModelVersion.is_active == True)
    )).scalar_one_or_none()

    if not active_mv:
        return {"tp": 0, "tn": 0, "fp": 0, "fn": 0, "total": 0}

    q = (
        select(
            func.sum(
                case((
                    (Prediction.predicted_label == 1) & (Transaction.true_label == 1), 1
                ), else_=0)
            ).label("tp"),
            func.sum(
                case((
                    (Prediction.predicted_label == 0) & (Transaction.true_label == 0), 1
                ), else_=0)
            ).label("tn"),
            func.sum(
                case((
                    (Prediction.predicted_label == 1) & (Transaction.true_label == 0), 1
                ), else_=0)
            ).label("fp"),
            func.sum(
                case((
                    (Prediction.predicted_label == 0) & (Transaction.true_label == 1), 1
                ), else_=0)
            ).label("fn"),
            func.count(Prediction.id).label("total"),
        )
        .join(Transaction, Prediction.transaction_id == Transaction.id)
        .where(Transaction.true_label.isnot(None))
        .where(Prediction.model_version_id == active_mv.id)
    )

    row = (await db.execute(q)).one()
    return {
        "tp": int(row.tp or 0),
        "tn": int(row.tn or 0),
        "fp": int(row.fp or 0),
        "fn": int(row.fn or 0),
        "total": int(row.total or 0),
        "model_version": active_mv.version_tag,
    }
