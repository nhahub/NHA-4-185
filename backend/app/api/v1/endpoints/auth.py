from typing import Optional
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.db.session import get_db
from app.api.deps import get_redis, get_current_user
from app.schemas.schemas import UserCreate, UserLogin, UserOut, TokenPair, TokenRefresh
from app.services.auth_service import AuthService
from app.models.models import User
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    svc = AuthService(db, redis)
    user = await svc.register(data)
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    svc = AuthService(db, redis)
    return await svc.login(data.email, data.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    svc = AuthService(db, redis)
    return await svc.refresh(data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
):
    svc = AuthService(db, redis)
    await svc.logout(str(current_user.id))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


@router.put("/me", response_model=UserOut)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Update own profile (full_name or password)."""
    if data.full_name:
        current_user.full_name = data.full_name
    if data.password:
        if len(data.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        from app.core.security import hash_password
        current_user.password_hash = hash_password(data.password)
    await db.flush()
    return current_user
