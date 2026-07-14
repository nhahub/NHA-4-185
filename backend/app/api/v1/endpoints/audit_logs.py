from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from app.db.session import get_db
from app.api.deps import require_role
from app.models.models import AuditLog, User, UserRole

router = APIRouter(prefix="/admin/audit-logs", tags=["Admin - Audit Logs"])


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    extra_data: dict
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=List[AuditLogOut])
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action name"),
    user_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(require_role(UserRole.admin)),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    q = q.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()
