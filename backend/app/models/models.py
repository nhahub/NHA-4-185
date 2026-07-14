import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Boolean, Float, Integer, SmallInteger,
    Text, Enum as SAEnum, ForeignKey, Numeric, ARRAY,
    DateTime, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


# ─── Enums ───────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin = "admin"
    analyst = "analyst"
    viewer = "viewer"


class TransactionSource(str, enum.Enum):
    upload = "upload"
    api = "api"
    manual = "manual"


class AlgorithmType(str, enum.Enum):
    logistic_regression = "logistic_regression"
    isolation_forest = "isolation_forest"
    xgboost = "xgboost"


class AlertSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    false_positive = "false_positive"


# ─── User ────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.analyst)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    transactions = relationship("Transaction", back_populates="uploader", foreign_keys="Transaction.uploaded_by")
    model_versions = relationship("ModelVersion", back_populates="trainer")
    assigned_alerts = relationship("FraudAlert", back_populates="assignee")
    audit_logs = relationship("AuditLog", back_populates="user")


# ─── Transaction ─────────────────────────────────────────────────────────────
class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_tx_id = Column(String(100), unique=True, nullable=True, index=True)
    time_seconds = Column(Float, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    # PCA features V1-V28 stored as array
    v_features = Column(ARRAY(Float), nullable=False)  # length 28
    true_label = Column(SmallInteger, nullable=True)   # nullable for real-time submissions
    source = Column(SAEnum(TransactionSource), default=TransactionSource.api)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    uploader = relationship("User", back_populates="transactions", foreign_keys=[uploaded_by])
    predictions = relationship("Prediction", back_populates="transaction")


# ─── ModelVersion ────────────────────────────────────────────────────────────
class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_tag = Column(String(50), unique=True, nullable=False)
    algorithm = Column(SAEnum(AlgorithmType), nullable=False)
    artifact_path = Column(Text, nullable=False)
    precision_score = Column(Float, nullable=True)
    recall_score = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    auc_roc = Column(Float, nullable=True)
    smote_applied = Column(Boolean, default=True)
    hyperparams = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=False, index=True)
    trained_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    trained_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    trainer = relationship("User", back_populates="model_versions")
    predictions = relationship("Prediction", back_populates="model_version")


# ─── Prediction ──────────────────────────────────────────────────────────────
class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    model_version_id = Column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False, index=True)
    predicted_label = Column(SmallInteger, nullable=False, index=True)
    fraud_probability = Column(Float, nullable=False)
    decision_threshold = Column(Float, nullable=False, default=0.5)
    is_correct = Column(Boolean, nullable=True)
    latency_ms = Column(Float, nullable=True)
    predicted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    transaction = relationship("Transaction", back_populates="predictions")
    model_version = relationship("ModelVersion", back_populates="predictions")
    alert = relationship("FraudAlert", back_populates="prediction", uselist=False)


# ─── FraudAlert ──────────────────────────────────────────────────────────────
class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id"), unique=True, nullable=False)
    severity = Column(SAEnum(AlertSeverity), nullable=False, index=True)
    status = Column(SAEnum(AlertStatus), default=AlertStatus.open, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    prediction = relationship("Prediction", back_populates="alert")
    assignee = relationship("User", back_populates="assigned_alerts")


# ─── AuditLog ────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    extra_data = Column("metadata", JSONB, default=dict)
    ip_address = Column(INET, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="audit_logs")
