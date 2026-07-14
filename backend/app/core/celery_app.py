from celery import Celery
from celery.signals import worker_process_init
from app.core.config import settings

celery_app = Celery(
    "fraud_detection",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.services.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@worker_process_init.connect
def _load_model_on_worker_startup(sender=None, **kwargs):
    """Load the ML model into ModelRegistry when the Celery worker starts."""
    import json, logging
    from pathlib import Path

    logger = logging.getLogger(__name__)
    artifacts = Path(settings.MODEL_ARTIFACTS_PATH)

    candidates = [
        ("xgboost",             artifacts / "xgboost.pkl",             artifacts / "xgboost_metadata.json"),
        ("logistic_regression", artifacts / "logistic_regression.pkl",  artifacts / "lr_metadata.json"),
    ]

    for model_name, model_path, meta_path in candidates:
        if not model_path.exists():
            continue

        scaler_path = artifacts / "scaler.pkl"
        if not scaler_path.exists():
            continue

        try:
            meta = {}
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)

            threshold = meta.get("threshold", settings.DEFAULT_THRESHOLD)

            fn_path = artifacts / "feature_names.json"
            si_path = artifacts / "scale_indices.json"
            feature_names = None
            scale_indices = None
            if fn_path.exists():
                with open(fn_path) as f:
                    feature_names = json.load(f)
            if si_path.exists():
                with open(si_path) as f:
                    scale_indices = json.load(f)

            version_tag = f"v2.0.0-{model_name}"

            # Get or create model version in DB using sync engine
            from sqlalchemy import create_engine, select
            from sqlalchemy.orm import Session
            from app.models.models import ModelVersion, AlgorithmType
            import uuid

            # Strip +asyncpg from DATABASE_URL to get sync driver
            db_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
            sync_engine = create_engine(db_url)

            with Session(sync_engine) as db:
                result = db.execute(
                    select(ModelVersion).where(ModelVersion.version_tag == version_tag)
                )
                mv = result.scalar_one_or_none()

                if not mv:
                    alg = AlgorithmType[model_name] if model_name in AlgorithmType.__members__ else AlgorithmType.logistic_regression
                    mv = ModelVersion(
                        version_tag=version_tag,
                        algorithm=alg,
                        artifact_path=str(model_path),
                        precision_score=meta.get("precision"),
                        recall_score=meta.get("recall"),
                        f1_score=meta.get("f1"),
                        auc_roc=meta.get("auc_roc"),
                        smote_applied=True,
                        hyperparams={
                            **meta.get("hyperparams", {}),
                            "threshold": threshold,
                            "pr_auc": meta.get("pr_auc"),
                            "model_path": str(model_path),
                            "scaler_path": str(scaler_path),
                        },
                        is_active=True,
                    )
                    db.add(mv)
                    all_mv = db.execute(select(ModelVersion)).scalars().all()
                    for m in all_mv:
                        if m.version_tag != version_tag:
                            m.is_active = False
                    db.commit()
                    db.refresh(mv)

                version_id = str(mv.id)
            sync_engine.dispose()

            from app.ml.model_registry import model_registry
            shap_path = artifacts / f"{model_name}_shap_explainer.pkl"
            model_registry.load(
                model_path=str(model_path),
                scaler_path=str(scaler_path),
                version_tag=version_tag,
                version_id=version_id,
                feature_names=feature_names,
                scale_indices=scale_indices,
                shap_explainer_path=str(shap_path) if shap_path.exists() else None,
            )
            model_registry.threshold = threshold
            logger.info(f"[Worker] Model loaded: {model_name} | threshold={threshold}")
            break

        except Exception as e:
            logger.warning(f"[Worker] Failed to load {model_name}: {e}")

    else:
        logger.warning("[Worker] No model artifacts found in worker process")
