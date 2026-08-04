from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.acta_observacion import acta_observacion_repo
from app.db.session import get_db
from app.models.compras import GuiaRemision
from app.models.inspeccion import ActaObservacion, InspeccionDetalle, Subsanacion
from app.schemas.common import Page
from app.schemas.inspeccion import (
    ActaObservacionCreate,
    ActaObservacionDetailOut,
    ActaObservacionOut,
    SubsanacionCreate,
    SubsanacionOut,
    SubsanacionReinspeccionUpdate,
)

router = APIRouter(prefix="/actas-observacion", tags=["Actas de observación"])

# Inspector levanta el acta; Admin puede intervenir administrativamente.
ROLES_INSPECCION = ("ADMIN", "INSPECTOR")
# "[Proveedor] presenta Subsanación (evidencia)" (docs sección 4.5) — mismo
# criterio de roles que registrar una guía de remisión en Módulo 3.
ROLES_SUBSANACION = ("ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR")


async def _almacen_id_de_inspeccion_detalle(db: AsyncSession, inspeccion_detalle_id: int) -> int | None:
    """RN-20: deriva el almacén destino de la guía a partir de una línea de
    inspección (InspeccionDetalle.guia_remision_detalle es lazy="joined",
    así que .guia_remision_id no cuesta una query extra)."""
    detalle = await db.get(InspeccionDetalle, inspeccion_detalle_id)
    if detalle is None:
        return None
    guia = await db.get(GuiaRemision, detalle.guia_remision_detalle.guia_remision_id)
    return guia.almacen_destino_id if guia else None


async def _almacen_id_de_acta(db: AsyncSession, acta_observacion_id: int) -> int | None:
    acta = await db.get(ActaObservacion, acta_observacion_id)
    if acta is None:
        return None
    return await _almacen_id_de_inspeccion_detalle(db, acta.inspeccion_detalle_id)


async def _almacen_id_de_subsanacion(db: AsyncSession, subsanacion_id: int) -> int | None:
    subsanacion = await db.get(Subsanacion, subsanacion_id)
    if subsanacion is None:
        return None
    return await _almacen_id_de_acta(db, subsanacion.acta_observacion_id)


@router.get("", response_model=Page[ActaObservacionOut])
async def listar_actas_observacion(
    page: int = 1,
    page_size: int = 20,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[ActaObservacionOut]:
    items, total = await acta_observacion_repo.list_filtrado(db, page=page, page_size=page_size, estado=estado)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{acta_observacion_id}", response_model=ActaObservacionDetailOut)
async def obtener_acta_observacion(
    acta_observacion_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> ActaObservacionDetailOut:
    acta = await acta_observacion_repo.get_con_detalle(db, acta_observacion_id)
    if acta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Acta de observación no encontrada")
    return ActaObservacionDetailOut.model_validate(acta)


@router.post(
    "/desde-inspeccion-detalle/{inspeccion_detalle_id}",
    response_model=ActaObservacionOut,
    status_code=status.HTTP_201_CREATED,
)
async def crear_acta_observacion(
    inspeccion_detalle_id: int,
    data: ActaObservacionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_INSPECCION)),
) -> ActaObservacionOut:
    """Solo se puede levantar sobre una línea de inspección con resultado
    OBSERVADO, y como máximo una vez por línea."""
    almacen_id = await _almacen_id_de_inspeccion_detalle(db, inspeccion_detalle_id)
    if almacen_id is not None:
        verificar_acceso_almacen(current, almacen_id)

    try:
        acta = await acta_observacion_repo.crear_acta(
            db, inspeccion_detalle_id, data, responsable_id=current.usuario_id
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de acta ya existe")

    await db.refresh(acta)
    return acta


@router.post(
    "/{acta_observacion_id}/subsanaciones", response_model=SubsanacionOut, status_code=status.HTTP_201_CREATED
)
async def crear_subsanacion(
    acta_observacion_id: int,
    data: SubsanacionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_SUBSANACION)),
) -> SubsanacionOut:
    almacen_id = await _almacen_id_de_acta(db, acta_observacion_id)
    if almacen_id is not None:
        verificar_acceso_almacen(current, almacen_id)

    try:
        subsanacion = await acta_observacion_repo.crear_subsanacion(db, acta_observacion_id, data)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.refresh(subsanacion)
    return subsanacion


@router.patch("/subsanaciones/{subsanacion_id}/reinspeccion", response_model=SubsanacionOut)
async def registrar_reinspeccion(
    subsanacion_id: int,
    data: SubsanacionReinspeccionUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_INSPECCION)),
) -> SubsanacionOut:
    """CONFORME -> acta SUBSANADA; NO_CONFORME -> acta RECHAZADA (terminal en
    este módulo). Si la guía ya no tiene actas ABIERTA, pasa a SUBSANADO."""
    almacen_id = await _almacen_id_de_subsanacion(db, subsanacion_id)
    if almacen_id is not None:
        verificar_acceso_almacen(current, almacen_id)

    try:
        subsanacion = await acta_observacion_repo.registrar_reinspeccion(
            db, subsanacion_id, data.resultado_reinspeccion, inspector_id=current.usuario_id
        )
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return subsanacion
