"""
FraudShield FastAPI application — v2.0
Improvements: XGBoost + SHAP + chronological split + feature engineering
"""
import json
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.middleware import AuditMiddleware
from app.core.rate_limit import limiter, rate_limit_handler
from app.db.session import engine, AsyncSessionLocal, Base
from app.api.v1.endpoints import auth, predict, alerts, analytics, transactions, admin_users, audit_logs
from app.ml.model_registry import model_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    # Auto-load best available model on startup
    artifacts = Path(settings.MODEL_ARTIFACTS_PATH)

    # Prefer XGBoost if available
    candidates = [
        ("xgboost",              artifacts / "xgboost.pkl",              artifacts / "xgboost_metadata.json"),
        ("logistic_regression",  artifacts / "logistic_regression.pkl",  artifacts / "lr_metadata.json"),
    ]

    loaded = False
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

            threshold  = meta.get("threshold", settings.DEFAULT_THRESHOLD)
            fn_path    = artifacts / "feature_names.json"
            si_path    = artifacts / "scale_indices.json"
            shap_path  = artifacts / f"{model_name}_shap_explainer.pkl"

            feature_names = None
            scale_indices = None
            if fn_path.exists():
                with open(fn_path) as f:
                    feature_names = json.load(f)
            if si_path.exists():
                with open(si_path) as f:
                    scale_indices = json.load(f)

            async with AsyncSessionLocal() as db:
                from app.models.models import ModelVersion, AlgorithmType
                from sqlalchemy import select

                alg = AlgorithmType[model_name] if model_name in AlgorithmType.__members__ else AlgorithmType.logistic_regression

                version_tag = f"v2.0.0-{model_name}"
                result = await db.execute(
                    select(ModelVersion).where(ModelVersion.version_tag == version_tag)
                )
                mv = result.scalar_one_or_none()

                if not mv:
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
                            "threshold":          threshold,
                            "pr_auc":             meta.get("pr_auc"),
                            "mcc":                meta.get("mcc"),
                            "model_path":         str(model_path),
                            "scaler_path":        str(scaler_path),
                            "shap_explainer_path": str(shap_path) if shap_path.exists() else None,
                            "split_strategy":     "chronological",
                            "pipeline_version":   "2.0",
                        },
                        is_active=True,
                    )
                    db.add(mv)
                    # Deactivate all others
                    all_mv = (await db.execute(select(ModelVersion))).scalars().all()
                    for m in all_mv:
                        if m.version_tag != version_tag:
                            m.is_active = False
                    await db.commit()
                    await db.refresh(mv)
                    logger.info(f"Registered {version_tag} in DB")

            # Load into registry
            model_registry.load(
                model_path=str(model_path),
                scaler_path=str(scaler_path),
                version_tag=version_tag,
                version_id=str(mv.id),
                shap_explainer_path=str(shap_path) if shap_path.exists() else None,
                feature_names=feature_names,
                scale_indices=scale_indices,
            )
            model_registry.threshold = threshold
            loaded = True
            logger.info(f"[Startup] {model_name} loaded | threshold={threshold:.3f} | SHAP={'✓' if model_registry.shap_explainer else '✗'}")
            break

        except Exception as e:
            logger.warning(f"[Startup] Failed to load {model_name}: {e}")

    if not loaded:
        logger.warning("[Startup] No model artifacts found. Run: python -m app.ml.pipeline.train")

    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="2.0.0",
    description=(
        "FraudShield — Credit Card Fraud Detection API\n\n"
        "v2.0 improvements: XGBoost + Optuna, SHAP explanations, "
        "chronological split, feature engineering, PR-AUC metric."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)
app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_handler)

PREFIX = "/api/v1"
app.include_router(auth.router,         prefix=PREFIX)
app.include_router(predict.router,      prefix=PREFIX)
app.include_router(alerts.router,       prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(analytics.router,    prefix=PREFIX)
app.include_router(admin_users.router,  prefix=PREFIX)
app.include_router(audit_logs.router,   prefix=PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message":  "FraudShield API v2.0",
        "docs":     "/docs",
        "version":  "2.0.0",
        "pipeline": "XGBoost + SHAP + chronological split",
        "health":   "/api/v1/health",
    }
