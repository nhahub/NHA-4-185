from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.api.deps import get_current_user, require_role
from app.schemas.schemas import TransactionOut
from app.models.models import Transaction, Prediction, User, UserRole

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("", response_model=List[TransactionOut])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    fraud_only: bool = Query(False),
    amount_min: Optional[float] = Query(None),
    amount_max: Optional[float] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all transactions with optional filters."""
    q = select(Transaction)

    if fraud_only:
        # join to predictions to filter by predicted fraud
        q = q.join(Prediction, Prediction.transaction_id == Transaction.id)\
             .where(Prediction.predicted_label == 1)

    if amount_min is not None:
        q = q.where(Transaction.amount >= amount_min)
    if amount_max is not None:
        q = q.where(Transaction.amount <= amount_max)

    q = q.order_by(Transaction.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats")
async def transaction_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate stats: total, fraud count, avg amount."""
    total = (await db.execute(select(func.count()).select_from(Transaction))).scalar()
    fraud_count = (await db.execute(
        select(func.count()).select_from(Prediction).where(Prediction.predicted_label == 1)
    )).scalar()
    avg_amount = (await db.execute(
        select(func.avg(Transaction.amount)).select_from(Transaction)
    )).scalar()

    return {
        "total": total or 0,
        "fraud_count": fraud_count or 0,
        "legitimate_count": (total or 0) - (fraud_count or 0),
        "fraud_rate": round((fraud_count or 0) / max(total or 1, 1), 6),
        "avg_amount": round(float(avg_amount or 0), 2),
    }


@router.get("/{tx_id}", response_model=TransactionOut)
async def get_transaction(
    tx_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single transaction by ID."""
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.delete("/{tx_id}", status_code=204)
async def delete_transaction(
    tx_id: UUID,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a transaction and its related predictions/alerts (admin only)."""
    result = await db.execute(select(Transaction).where(Transaction.id == tx_id))
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(tx)
    await db.flush()


import csv, io
from fastapi.responses import StreamingResponse

@router.get("/export")
async def export_transactions(
    fraud_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream transactions as a CSV file download."""
    q = (
        select(Transaction, Prediction)
        .outerjoin(Prediction, Prediction.transaction_id == Transaction.id)
        .order_by(Transaction.created_at.desc())
        .limit(50000)
    )
    if fraud_only:
        q = q.where(Prediction.predicted_label == 1)

    result = await db.execute(q)
    rows   = result.fetchall()

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "amount", "time_seconds", "source", "true_label",
            "predicted_label", "fraud_probability", "created_at",
        ])
        yield buf.getvalue(); buf.seek(0); buf.truncate(0)

        for tx, pred in rows:
            writer.writerow([
                str(tx.id), float(tx.amount), tx.time_seconds,
                tx.source, tx.true_label,
                pred.predicted_label if pred else "",
                round(pred.fraud_probability, 4) if pred else "",
                tx.created_at.isoformat(),
            ])
            yield buf.getvalue(); buf.seek(0); buf.truncate(0)

    fname = "fraud_transactions.csv" if fraud_only else "transactions.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
