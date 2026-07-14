from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.models import AuditLog
from app.core.security import decode_token
import uuid
import re

# Map HTTP method + path pattern → action name
ACTION_MAP = [
    (r"POST",   r"/auth/login",          "USER_LOGIN"),
    (r"POST",   r"/auth/register",       "USER_REGISTER"),
    (r"POST",   r"/auth/logout",         "USER_LOGOUT"),
    (r"POST",   r"/predict/single",      "PREDICT_SINGLE"),
    (r"POST",   r"/predict/batch",       "PREDICT_BATCH_UPLOAD"),
    (r"POST",   r"/transactions/upload", "TRANSACTION_UPLOAD"),
    (r"DELETE", r"/transactions/",       "TRANSACTION_DELETE"),
    (r"PUT",    r"/alerts/",             "ALERT_UPDATE"),
    (r"POST",   r"/models/.*/activate",  "MODEL_ACTIVATE"),
    (r"PATCH",  r"/admin/users/",        "ADMIN_USER_UPDATE"),
    (r"DELETE", r"/admin/users/",        "ADMIN_USER_DEACTIVATE"),
]

SKIP_PATHS = {"/api/v1/health", "/docs", "/openapi.json", "/"}


def _resolve_action(method: str, path: str) -> str | None:
    for m, pattern, action in ACTION_MAP:
        if method == m and re.search(pattern, path):
            return action
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        path = request.url.path
        method = request.method

        # Only log mutating requests that succeeded
        if path in SKIP_PATHS or method == "GET":
            return response
        if response.status_code >= 400:
            return response

        action = _resolve_action(method, path)
        if not action:
            return response

        # Extract user_id from JWT if present
        user_id = None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                payload = decode_token(auth[7:])
                user_id = uuid.UUID(payload.get("sub")) if payload.get("sub") else None
            except Exception:
                pass

        # Write audit log in background (non-blocking)
        ip = request.client.host if request.client else None
        try:
            async with AsyncSessionLocal() as db:
                log = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=path.split("/")[3] if len(path.split("/")) > 3 else None,
                    extra_data={"method": method, "path": path, "status": response.status_code},
                    ip_address=ip,
                )
                db.add(log)
                await db.commit()
        except Exception:
            pass  # Never let audit logging break the main request

        return response
