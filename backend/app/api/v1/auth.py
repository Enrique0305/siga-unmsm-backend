from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.crud.usuario import usuario_repo
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


async def _emitir_tokens(db: AsyncSession, usuario_id: int, rol_nombre: str, acceso_todos: bool) -> TokenResponse:
    almacenes = [] if acceso_todos else await usuario_repo.get_almacen_ids(db, usuario_id)
    access = create_access_token(usuario_id, rol_nombre, almacenes, acceso_todos)
    refresh = create_refresh_token(usuario_id)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    usuario = await usuario_repo.get_by_correo(db, payload.correo)
    if usuario is None or not verify_password(payload.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Correo o contraseña incorrectos")
    if usuario.estado != "ACTIVO":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo, contacte al administrador")

    return await _emitir_tokens(db, usuario.usuario_id, usuario.rol.nombre, usuario.rol.acceso_todos_almacenes)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    data = decode_token(payload.refresh_token)
    if data is None or data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

    usuario = await usuario_repo.get(db, int(data["sub"]))
    if usuario is None or usuario.estado != "ACTIVO":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado o inactivo")

    return await _emitir_tokens(db, usuario.usuario_id, usuario.rol.nombre, usuario.rol.acceso_todos_almacenes)
