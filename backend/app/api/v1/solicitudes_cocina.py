from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.solicitud_cocina import solicitud_cocina_repo
from app.db.session import get_db
from app.models.organizacion import CentroConsumo
from app.schemas.cocina import SolicitudCocinaCreate, SolicitudCocinaDetailOut, SolicitudCocinaEstadoUpdate, SolicitudCocinaOut
from app.schemas.common import Page

router = APIRouter(prefix="/solicitudes-cocina", tags=["Solicitudes de cocina"])

# "[Cocina] revisa Menú del día -> genera Solicitud Diaria de Insumos" (docs sección 4.4)
ROLES_EDICION = ("ADMIN", "COCINA")


@router.get("", response_model=Page[SolicitudCocinaOut])
async def listar_solicitudes(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    centro_consumo_id: int | None = None,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[SolicitudCocinaOut]:
    items, total = await solicitud_cocina_repo.list_filtrado(
        db, page=page, page_size=page_size, almacen_id=almacen_id, centro_consumo_id=centro_consumo_id, estado=estado
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{solicitud_cocina_id}", response_model=SolicitudCocinaDetailOut)
async def obtener_solicitud(
    solicitud_cocina_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> SolicitudCocinaDetailOut:
    solicitud = await solicitud_cocina_repo.get_con_detalle(db, solicitud_cocina_id)
    if solicitud is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de cocina no encontrada")
    return SolicitudCocinaDetailOut.from_model(solicitud)


@router.post("", response_model=SolicitudCocinaDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_solicitud(
    data: SolicitudCocinaCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> SolicitudCocinaDetailOut:
    """RN-07/21 (no excede el disponible) · RN-17 (el almacén se deriva del
    centro de consumo, nunca lo manda el cliente). Reserva stock_comprometido
    por cada línea y calcula cantidad_teorica_bom desde dosificacion_detalle."""
    centro_consumo = await db.get(CentroConsumo, data.centro_consumo_id)
    if centro_consumo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El centro de consumo indicado no existe")
    verificar_acceso_almacen(current, centro_consumo.almacen_id)

    try:
        solicitud = await solicitud_cocina_repo.crear(db, data, solicitado_por_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de solicitud ya existe")

    solicitud = await solicitud_cocina_repo.get_con_detalle(db, solicitud.solicitud_cocina_id)
    return SolicitudCocinaDetailOut.from_model(solicitud)


@router.patch("/{solicitud_cocina_id}/estado", response_model=SolicitudCocinaOut)
async def cambiar_estado_solicitud(
    solicitud_cocina_id: int,
    data: SolicitudCocinaEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> SolicitudCocinaOut:
    """Única transición soportada: PENDIENTE -> ANULADA, libera la reserva
    de stock_comprometido de cada línea."""
    solicitud = await solicitud_cocina_repo.get_con_detalle(db, solicitud_cocina_id)
    if solicitud is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud de cocina no encontrada")
    verificar_acceso_almacen(current, solicitud.almacen_id)

    try:
        if data.estado == "ANULADA":
            await solicitud_cocina_repo.anular(db, solicitud)
        else:
            solicitud_cocina_repo.validar_transicion(solicitud.estado, data.estado)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.commit()
    await db.refresh(solicitud)
    return solicitud
