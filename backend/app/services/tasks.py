"""
Celery batch prediction task — updated for new ModelRegistry API.
"""
import asyncio
import pandas as pd
from io import StringIO
from app.core.celery_app import celery_app
from app.models.models import Transaction, Prediction, FraudAlert, AlertStatus
from app.ml.model_registry import model_registry
from app.services.prediction_service import _severity_from_prob
import uuid
from datetime import timezone
import time


@celery_app.task(bind=True, name="tasks.batch_predict")
def batch_predict_task(self, csv_content: str, user_id: str):
    self.update_state(state="STARTED", meta={"processed": 0, "total": 0})
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(_async_batch(self, csv_content, user_id))
    loop.close()
    return result


async def _async_batch(task, csv_content: str, user_id: str):
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from app.core.config import settings

    # Create a fresh engine bound to THIS event loop
    engine = create_async_engine(settings.DATABASE_URL, pool_size=5)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    df = pd.read_csv(StringIO(csv_content))

    required = ["Time", "Amount"] + [f"V{i}" for i in range(1, 29)]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        await engine.dispose()
        return {"status": "failed", "error": f"Missing columns: {missing}"}

    total      = len(df)
    fraud_count = 0
    uid        = uuid.UUID(user_id)

    task.update_state(state="STARTED", meta={"processed": 0, "total": total})

    async with SessionLocal() as db:
        try:
            transactions = []
            rows_for_inference = []

            for _, row in df.iterrows():
                v_features = [float(row[f"V{i}"]) for i in range(1, 29)]
                tx = Transaction(
                    time_seconds=float(row["Time"]),
                    amount=float(row["Amount"]),
                    v_features=v_features,
                    true_label=int(row["Class"]) if "Class" in df.columns else None,
                    source="upload",
                    uploaded_by=uid,
                )
                db.add(tx)
                transactions.append(tx)
                rows_for_inference.append({
                    "time_seconds": float(row["Time"]),
                    "amount":       float(row["Amount"]),
                    "v_features":   v_features,
                })

            await db.flush()

            # Batch inference
            t0 = time.perf_counter()
            labels, probas = model_registry.predict_batch(rows_for_inference)
            latency_each   = ((time.perf_counter() - t0) * 1000) / max(total, 1)

            model_vid = uuid.UUID(model_registry.active_version_id)

            for tx, label, prob in zip(transactions, labels, probas):
                pred = Prediction(
                    transaction_id=tx.id,
                    model_version_id=model_vid,
                    predicted_label=int(label),
                    fraud_probability=float(prob),
                    decision_threshold=model_registry.threshold,
                    latency_ms=round(latency_each, 2),
                )
                db.add(pred)
                await db.flush()

                if label == 1:
                    fraud_count += 1
                    db.add(FraudAlert(
                        prediction_id=pred.id,
                        severity=_severity_from_prob(float(prob)),
                        status=AlertStatus.open,
                    ))

            await db.commit()

        except Exception as e:
            await db.rollback()
            await engine.dispose()
            return {"status": "failed", "error": str(e)}

    await engine.dispose()
    return {
        "status":           "completed",
        "total":            total,
        "fraud_count":      fraud_count,
        "legitimate_count": total - fraud_count,
        "fraud_rate":       round(fraud_count / total, 4) if total else 0,
    }
