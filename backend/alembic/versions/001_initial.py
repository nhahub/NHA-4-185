"""Initial schema - all tables

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, ARRAY

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────────────────────
    user_role = sa.Enum("admin", "analyst", "viewer", name="userrole")
    tx_source  = sa.Enum("upload", "api", "manual", name="transactionsource")
    algorithm  = sa.Enum("logistic_regression", "isolation_forest", name="algorithmtype")
    severity   = sa.Enum("low", "medium", "high", "critical", name="alertseverity")
    alert_status = sa.Enum("open", "investigating", "resolved", "false_positive", name="alertstatus")

    for e in [user_role, tx_source, algorithm, severity, alert_status]:
        e.create(op.get_bind(), checkfirst=True)

    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("role", sa.Enum("admin","analyst","viewer", name="userrole"), nullable=False, server_default="analyst"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── transactions ───────────────────────────────────────────────────────
    op.create_table(
        "transactions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("external_tx_id", sa.String(100), nullable=True),
        sa.Column("time_seconds", sa.Float, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("v_features", ARRAY(sa.Float), nullable=False),
        sa.Column("true_label", sa.SmallInteger, nullable=True),
        sa.Column("source", sa.Enum("upload","api","manual", name="transactionsource"), server_default="api"),
        sa.Column("uploaded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_external_tx_id", "transactions", ["external_tx_id"], unique=True)
    op.create_index("ix_transactions_created_at", "transactions", ["created_at"])
    op.create_index("ix_transactions_amount", "transactions", ["amount"])

    # ── model_versions ─────────────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("version_tag", sa.String(20), nullable=False),
        sa.Column("algorithm", sa.Enum("logistic_regression","isolation_forest", name="algorithmtype"), nullable=False),
        sa.Column("artifact_path", sa.Text, nullable=False),
        sa.Column("precision_score", sa.Float, nullable=True),
        sa.Column("recall_score", sa.Float, nullable=True),
        sa.Column("f1_score", sa.Float, nullable=True),
        sa.Column("auc_roc", sa.Float, nullable=True),
        sa.Column("smote_applied", sa.Boolean, server_default="true"),
        sa.Column("hyperparams", JSONB, server_default="{}"),
        sa.Column("is_active", sa.Boolean, server_default="false"),
        sa.Column("trained_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("trained_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_model_versions_version_tag", "model_versions", ["version_tag"], unique=True)
    op.create_index("ix_model_versions_is_active", "model_versions", ["is_active"])

    # ── predictions ────────────────────────────────────────────────────────
    op.create_table(
        "predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("model_version_id", UUID(as_uuid=True), sa.ForeignKey("model_versions.id"), nullable=False),
        sa.Column("predicted_label", sa.SmallInteger, nullable=False),
        sa.Column("fraud_probability", sa.Float, nullable=False),
        sa.Column("decision_threshold", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("is_correct", sa.Boolean, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("predicted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_predictions_predicted_label", "predictions", ["predicted_label"])
    op.create_index("ix_predictions_predicted_at", "predictions", ["predicted_at"])
    op.create_index("ix_predictions_transaction_id", "predictions", ["transaction_id"])

    # ── fraud_alerts ───────────────────────────────────────────────────────
    op.create_table(
        "fraud_alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("prediction_id", UUID(as_uuid=True), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("severity", sa.Enum("low","medium","high","critical", name="alertseverity"), nullable=False),
        sa.Column("status", sa.Enum("open","investigating","resolved","false_positive", name="alertstatus"), server_default="open"),
        sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fraud_alerts_prediction_id", "fraud_alerts", ["prediction_id"], unique=True)
    op.create_index("ix_fraud_alerts_severity", "fraud_alerts", ["severity"])
    op.create_index("ix_fraud_alerts_status", "fraud_alerts", ["status"])

    # ── audit_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("fraud_alerts")
    op.drop_table("predictions")
    op.drop_table("model_versions")
    op.drop_table("transactions")
    op.drop_table("users")

    for name in ["alertstatus", "alertseverity", "algorithmtype", "transactionsource", "userrole"]:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
