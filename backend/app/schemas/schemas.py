from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from app.models.models import UserRole, AlertSeverity, AlertStatus, AlgorithmType


# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=100)
    role: UserRole = UserRole.analyst


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# ═══════════════════════════════════════════════════════════
# TRANSACTION
# ═══════════════════════════════════════════════════════════
class TransactionCreate(BaseModel):
    time_seconds: float = Field(ge=0, le=200000)
    amount: float = Field(gt=0, le=30000)
    v1: float  = Field(ge=-30, le=30)
    v2: float  = Field(ge=-30, le=30)
    v3: float  = Field(ge=-30, le=30)
    v4: float  = Field(ge=-30, le=30)
    v5: float  = Field(ge=-30, le=30)
    v6: float  = Field(ge=-30, le=30)
    v7: float  = Field(ge=-30, le=30)
    v8: float  = Field(ge=-30, le=30)
    v9: float  = Field(ge=-30, le=30)
    v10: float = Field(ge=-30, le=30)
    v11: float = Field(ge=-30, le=30)
    v12: float = Field(ge=-30, le=30)
    v13: float = Field(ge=-30, le=30)
    v14: float = Field(ge=-30, le=30)
    v15: float = Field(ge=-30, le=30)
    v16: float = Field(ge=-30, le=30)
    v17: float = Field(ge=-30, le=30)
    v18: float = Field(ge=-30, le=30)
    v19: float = Field(ge=-30, le=30)
    v20: float = Field(ge=-30, le=30)
    v21: float = Field(ge=-30, le=30)
    v22: float = Field(ge=-30, le=30)
    v23: float = Field(ge=-30, le=30)
    v24: float = Field(ge=-30, le=30)
    v25: float = Field(ge=-30, le=30)
    v26: float = Field(ge=-30, le=30)
    v27: float = Field(ge=-30, le=30)
    v28: float = Field(ge=-30, le=30)

    def to_feature_list(self) -> List[float]:
        return [
            self.time_seconds, self.amount,
            self.v1,  self.v2,  self.v3,  self.v4,  self.v5,
            self.v6,  self.v7,  self.v8,  self.v9,  self.v10,
            self.v11, self.v12, self.v13, self.v14, self.v15,
            self.v16, self.v17, self.v18, self.v19, self.v20,
            self.v21, self.v22, self.v23, self.v24, self.v25,
            self.v26, self.v27, self.v28,
        ]


class TransactionOut(BaseModel):
    id: UUID
    time_seconds: float
    amount: float
    true_label: Optional[int]
    source: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# SHAP
# ═══════════════════════════════════════════════════════════
class ShapFeature(BaseModel):
    feature: str
    value: float
    shap_value: float
    direction: str   # "fraud" | "legitimate"


# ═══════════════════════════════════════════════════════════
# PREDICTION
# ═══════════════════════════════════════════════════════════
class PredictionResult(BaseModel):
    prediction_id: UUID
    transaction_id: UUID
    predicted_label: int
    fraud_probability: float
    decision_threshold: float
    is_fraud: bool
    alert_id: Optional[UUID]
    latency_ms: float
    model_version: str
    shap_explanation: Optional[List[ShapFeature]] = None
    model_config = {"from_attributes": True}


class PredictionOut(BaseModel):
    id: UUID
    transaction_id: UUID
    predicted_label: int
    fraud_probability: float
    is_correct: Optional[bool]
    latency_ms: Optional[float]
    predicted_at: datetime
    model_config = {"from_attributes": True}


class BatchJobStatus(BaseModel):
    job_id: str
    status: str
    total: Optional[int] = None
    processed: Optional[int] = None
    fraud_count: Optional[int] = None


# ═══════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════
class AlertOut(BaseModel):
    id: UUID
    prediction_id: UUID
    severity: AlertSeverity
    status: AlertStatus
    fraud_probability: Optional[float] = None
    assigned_to: Optional[UUID]
    notes: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    model_config = {"from_attributes": True}


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════
# MODEL VERSIONS
# ═══════════════════════════════════════════════════════════
class ModelVersionOut(BaseModel):
    id: UUID
    version_tag: str
    algorithm: AlgorithmType
    precision_score: Optional[float]
    recall_score: Optional[float]
    f1_score: Optional[float]
    auc_roc: Optional[float]
    smote_applied: bool
    hyperparams: dict
    is_active: bool
    trained_at: datetime
    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════
class DashboardStats(BaseModel):
    total_transactions: int
    total_fraud: int
    fraud_rate: float
    precision: Optional[float]
    recall: Optional[float]
    auc_roc: Optional[float]
    pr_auc: Optional[float]
    mcc: Optional[float]
    open_alerts: int
    today_transactions: int
    today_fraud: int


class HealthStatus(BaseModel):
    status: str
    database: str
    redis: str
    ml_model: str
    shap_loaded: bool
    version: str
