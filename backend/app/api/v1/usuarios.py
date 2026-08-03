from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.usuario import usuario_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.usuario import UsuarioCreate, UsuarioOut

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


async def _to_out(db: AsyncSession, usuario) -> UsuarioOut:
    almacen_ids = await usuario_repo.get_almacen_ids(db, usuario.usuario_id)
    return UsuarioOut.model_validate({**usuario.__dict__, "rol": usuario.rol, "almacen_ids": almacen_ids})


@router.get("", response_model=Page[UsuarioOut])
async def listar_usuarios(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles("ADMIN")),
) -> Page[UsuarioOut]:
    items, total = await usuario_repo.list_paginated(db, page=page, page_size=page_size)
    return Page(items=[await _to_out(db, u) for u in items], total=total, page=page, page_size=page_size)


@router.get("/me", response_model=UsuarioOut)
async def mi_perfil(
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> UsuarioOut:
    usuario = await usuario_repo.get(db, current.usuario_id)
    if usuario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return await _to_out(db, usuario)


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
async def crear_usuario(
    data: UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles("ADMIN")),
) -> UsuarioOut:
    try:
        usuario = await usuario_repo.create_con_almacenes(db, data)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo ya está registrado")
    await db.refresh(usuario, attribute_names=["rol"])
    return await _to_out(db, usuario)
