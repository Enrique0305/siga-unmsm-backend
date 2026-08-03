from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.requerimiento import requerimiento_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.requerimiento import (
    RequerimientoAnualCreate,
    RequerimientoAnualDetailOut,
    RequerimientoAnualDetalleOut,
    RequerimientoAnualEstadoUpdate,
    RequerimientoAnualOut,
)

router = APIRouter(prefix="/requerimientos-anuales", tags=["Requerimiento anual de insumos"])

# Nutrición arma el requerimiento; Logística también puede aprobarlo (RN
# sección 4.1: "Nutrición envía a aprobación -> Administrador/Logística aprueba").
ROLES_CREACION = ("ADMIN", "NUTRICION")
ROLES_APROBACION = ("ADMIN", "NUTRICION", "LOGISTICA_CENTRAL")


def _build_detail(requerimiento) -> RequerimientoAnualDetailOut:
    base = RequerimientoAnualOut.model_validate(requerimiento)
    return RequerimientoAnualDetailOut(
        **base.model_dump(),
        detalle=[RequerimientoAnualDetalleOut.from_model(d) for d in requerimiento.detalle],
    )


@router.get("", response_model=Page[RequerimientoAnualOut])
async def listar_requerimientos(
    page: int = 1,
    page_size: int = 20,
    estado: str | None = None,
    racion_anual_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[RequerimientoAnualOut]:
    items, total = await requerimiento_repo.list_filtrado(
        db, page=page, page_size=page_size, estado=estado, racion_anual_id=racion_anual_id
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{requerimiento_anual_id}", response_model=RequerimientoAnualDetailOut)
async def obtener_requerimiento(
    requerimiento_anual_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> RequerimientoAnualDetailOut:
    requerimiento = await requerimiento_repo.get_con_detalle(db, requerimiento_anual_id)
    if requerimiento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requerimiento anual no encontrado")
    return _build_detail(requerimiento)


@router.post("", response_model=RequerimientoAnualDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_requerimiento(
    data: RequerimientoAnualCreate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_CREACION)),
) -> RequerimientoAnualDetailOut:
    try:
        requerimiento = await requerimiento_repo.crear_con_detalle(db, data)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No se pudo registrar el requerimiento")

    requerimiento = await requerimiento_repo.get_con_detalle(db, requerimiento.requerimiento_anual_id)
    return _build_detail(requerimiento)


@router.patch("/{requerimiento_anual_id}/estado", response_model=RequerimientoAnualOut)
async def cambiar_estado_requerimiento(
    requerimiento_anual_id: int,
    data: RequerimientoAnualEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_APROBACION)),
) -> RequerimientoAnualOut:
    requerimiento = await requerimiento_repo.get(db, requerimiento_anual_id)
    if requerimiento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requerimiento anual no encontrado")

    try:
        requerimiento_repo.validar_transicion(requerimiento.estado, data.estado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    requerimiento_repo.aplicar_transicion(requerimiento, data.estado, aprobado_por_id=current.usuario_id)
    await db.commit()
    await db.refresh(requerimiento)
    return requerimiento
