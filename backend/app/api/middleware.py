from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.audit import current_usuario_id
from app.core.security import decode_token


class AuditContextMiddleware(BaseHTTPMiddleware):
    """Decodifica el Bearer token (reusando decode_token, sin reimplementar
    JWT) y deja el usuario_id disponible en un ContextVar para que el evento
    de auditoría de core/audit.py lo pueda leer — un evento de SQLAlchemy no
    tiene acceso a la request de FastAPI de otra forma."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        usuario_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            payload = decode_token(auth_header[7:])
            if payload is not None and payload.get("type") == "access":
                usuario_id = int(payload["sub"])

        token = current_usuario_id.set(usuario_id)
        try:
            return await call_next(request)
        finally:
            current_usuario_id.reset(token)
