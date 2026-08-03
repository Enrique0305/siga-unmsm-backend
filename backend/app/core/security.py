from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def _create_token(subject: str, expires_delta: timedelta, extra_claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {"sub": subject, "iat": now, "exp": now + expires_delta}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(usuario_id: int, rol: str, almacenes: list[int], acceso_todos_almacenes: bool) -> str:
    """
    El token lleva el rol y los almacenes autorizados en el payload
    (claims), así el backend no necesita consultar usuario_almacen_acceso
    en cada request para validar el alcance por almacén (RN-20).
    """
    return _create_token(
        subject=str(usuario_id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra_claims={
            "type": "access",
            "rol": rol,
            "almacenes": almacenes,
            "acceso_todos_almacenes": acceso_todos_almacenes,
        },
    )


def create_refresh_token(usuario_id: int) -> str:
    return _create_token(
        subject=str(usuario_id),
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        extra_claims={"type": "refresh"},
    )


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
