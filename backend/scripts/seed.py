"""
Seed script — run once after docker compose up.
Usage: docker compose exec backend python -m scripts.seed
"""
import asyncio, json, uuid
from pathlib import Path
from sqlalchemy import select

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal, engine, Base
from app.models.models import User, UserRole, ModelVersion, AlgorithmType
from app.core.security import hash_password

ARTIFACTS = Path(__file__).parent.parent / "app" / "ml" / "artifacts"

SEED_USERS = [
    {"email": "admin@fraudshield.com",   "password": "Admin1234!",
     "full_name": "System Admin",         "role": UserRole.admin},
    {"email": "analyst@fraudshield.com", "password": "Analyst1234!",
     "full_name": "Default Analyst",      "role": UserRole.analyst},
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # ── Users ─────────────────────────────────────────────────────────────
        for u in SEED_USERS:
            existing = (await db.execute(
                select(User).where(User.email == u["email"])
            )).scalar_one_or_none()
            if existing:
                print(f"[Seed] User exists: {u['email']}")
                continue
            db.add(User(
                email=u["email"],
                password_hash=hash_password(u["password"]),
                full_name=u["full_name"],
                role=u["role"],
                is_active=True,
            ))
            print(f"[Seed] Created: {u['email']} ({u['role']})")
        await db.flush()

        # ── Model versions (prefer XGBoost, fallback to LR) ───────────────────
        candidates = [
            ("xgboost",             "xgboost.pkl",             "xgboost_metadata.json",   AlgorithmType.xgboost),
            ("logistic_regression", "logistic_regression.pkl", "lr_metadata.json",         AlgorithmType.logistic_regression),
        ]
        registered = False
        for name, pkl, meta_file, alg in candidates:
            model_path = ARTIFACTS / pkl
            scaler_path = ARTIFACTS / "scaler.pkl"
            meta_path  = ARTIFACTS / meta_file
            if not model_path.exists() or not scaler_path.exists():
                continue

            meta = {}
            if meta_path.exists():
                with open(meta_path) as f:
                    meta = json.load(f)

            version_tag = f"v2.0.0-{name}"
            existing_mv = (await db.execute(
                select(ModelVersion).where(ModelVersion.version_tag == version_tag)
            )).scalar_one_or_none()

            if not existing_mv:
                shap_path = ARTIFACTS / f"{name}_shap_explainer.pkl"
                db.add(ModelVersion(
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
                        "threshold":           meta.get("threshold", 0.5),
                        "pr_auc":              meta.get("pr_auc"),
                        "mcc":                 meta.get("mcc"),
                        "model_path":          str(model_path),
                        "scaler_path":         str(scaler_path),
                        "shap_explainer_path": str(shap_path) if shap_path.exists() else None,
                        "split_strategy":      "chronological",
                        "pipeline_version":    "2.0",
                    },
                    is_active=not registered,   # first found = active
                ))
                print(f"[Seed] Registered {version_tag}")
                registered = True
            else:
                print(f"[Seed] {version_tag} already registered")

        if not registered:
            print("[Seed] No model artifacts found — run: python -m app.ml.pipeline.train")

        await db.commit()

    print("\n[Seed] ✓ Done")
    print("  Admin:   admin@fraudshield.com   / Admin1234!")
    print("  Analyst: analyst@fraudshield.com / Analyst1234!")


if __name__ == "__main__":
    asyncio.run(seed())
