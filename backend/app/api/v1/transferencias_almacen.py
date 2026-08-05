from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.transferencia_almacen import transferencia_almacen_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.inventario import (
    TransferenciaAlmacenCreate,
    TransferenciaAlmacenDetailOut,
    TransferenciaAlmacenOut,
    TransferenciaRecepcionIn,
)

router = APIRouter(prefix="/transferencias", tags=["Transferencias entre almacenes"])

ROLES_EDICION = ("ADMIN", "ALMACENERO")


@router.get("", response_model=Page[TransferenciaAlmacenOut])
async def listar_transferencias(
    page: int = 1,
    page_size: int = 20,
    almacen_origen_id: int | None = None,
    almacen_destino_id: int | None = None,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[TransferenciaAlmacenOut]:
    """RN-20 en lecturas: visible si el usuario tiene acceso a origen O
    destino (política ANY, ver Sesión 15) — no se usa `resolver_almacenes_
    visibles` porque hay dos columnas de almacén, no una."""
    items, total = await transferencia_almacen_repo.list_filtrado(
        db,
        page=page,
        page_size=page_size,
        almacen_origen_id=almacen_origen_id,
        almacen_destino_id=almacen_destino_id,
        almacen_ids=None if current.acceso_todos_almacenes else current.almacenes,
        estado=estado,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{transferencia_id}", response_model=TransferenciaAlmacenDetailOut)
async def obtener_transferencia(
    transferencia_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> TransferenciaAlmacenDetailOut:
    transferencia = await transferencia_almacen_repo.get_con_detalle(db, transferencia_id)
    if transferencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada")
    if not (
        current.tiene_acceso_almacen(transferencia.almacen_origen_id)
        or current.tiene_acceso_almacen(transferencia.almacen_destino_id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes autorización para operar sobre este almacén (RN-20)",
        )
    return TransferenciaAlmacenDetailOut.from_model(transferencia)


@router.post("", response_model=TransferenciaAlmacenDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_transferencia(
    data: TransferenciaAlmacenCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> TransferenciaAlmacenDetailOut:
    """RN-18: la salida se descuenta del origen de inmediato; el destino solo
    se incrementa al confirmar la recepción (POST .../recepcion)."""
    verificar_acceso_almacen(current, data.almacen_origen_id)

    try:
        transferencia = await transferencia_almacen_repo.crear(db, data, responsable_origen_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de transferencia ya existe")

    transferencia = await transferencia_almacen_repo.get_con_detalle(db, transferencia.transferencia_id)
    return TransferenciaAlmacenDetailOut.from_model(transferencia)


@router.post("/{transferencia_id}/recepcion", response_model=TransferenciaAlmacenDetailOut)
async def recibir_transferencia(
    transferencia_id: int,
    data: TransferenciaRecepcionIn,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> TransferenciaAlmacenDetailOut:
    transferencia = await transferencia_almacen_repo.get_con_detalle(db, transferencia_id)
    if transferencia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada")
    verificar_acceso_almacen(current, transferencia.almacen_destino_id)

    try:
        await transferencia_almacen_repo.registrar_recepcion(db, transferencia, data, responsable_destino_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    transferencia = await transferencia_almacen_repo.get_con_detalle(db, transferencia_id)
    return TransferenciaAlmacenDetailOut.from_model(transferencia)
