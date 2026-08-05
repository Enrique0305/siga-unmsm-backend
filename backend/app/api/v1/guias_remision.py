from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_current_user,
    require_roles,
    verificar_acceso_almacen,
    verificar_acceso_proveedor,
)
from app.crud.guia_remision import guia_remision_repo
from app.db.session import get_db
from app.models.compras import GuiaRemision
from app.schemas.common import Page
from app.schemas.compra import (
    GuiaRemisionCreate,
    GuiaRemisionDetalleIn,
    GuiaRemisionDetalleOut,
    GuiaRemisionDetailOut,
    GuiaRemisionListOut,
)

router = APIRouter(prefix="/guias-remision", tags=["Guías de remisión"])

# "[Proveedor] entrega insumos -> sube/registra Guía de Remisión" (docs sección 4.3);
# el rol PROVEEDOR ya existe en seed.py para esto. LOGISTICA_CENTRAL/ADMIN pueden
# registrar en nombre del proveedor si hace falta.
ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR")


def _build_detail(guia) -> GuiaRemisionDetailOut:
    base = GuiaRemisionListOut.from_model(guia)
    return GuiaRemisionDetailOut(
        **base.model_dump(),
        detalle=[GuiaRemisionDetalleOut.from_model(d) for d in guia.detalle],
    )


@router.get("", response_model=Page[GuiaRemisionListOut])
async def listar_guias_remision(
    page: int = 1,
    page_size: int = 20,
    orden_compra_id: int | None = None,
    proveedor_id: int | None = None,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[GuiaRemisionListOut]:
    if current.rol == "PROVEEDOR":
        proveedor_id = current.proveedor_id
    items, total = await guia_remision_repo.list_filtrado(
        db,
        page=page,
        page_size=page_size,
        orden_compra_id=orden_compra_id,
        proveedor_id=proveedor_id,
        estado=estado,
    )
    return Page(
        items=[GuiaRemisionListOut.from_model(g) for g in items], total=total, page=page, page_size=page_size
    )


@router.get("/{guia_remision_id}", response_model=GuiaRemisionDetailOut)
async def obtener_guia_remision(
    guia_remision_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> GuiaRemisionDetailOut:
    guia = await guia_remision_repo.get_con_detalle(db, guia_remision_id)
    if guia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guía de remisión no encontrada")
    verificar_acceso_proveedor(current, guia.proveedor_id)
    return _build_detail(guia)


@router.post("", response_model=GuiaRemisionDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_guia_remision(
    data: GuiaRemisionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> GuiaRemisionDetailOut:
    """RN-02 (vinculada a OC + pedido semanal) · RN-03 (cantidad entregada no
    excede el saldo pendiente de la línea de OC) · RN-13 (almacén destino
    obligatorio, ya forzado por el esquema)."""
    verificar_acceso_almacen(current, data.almacen_destino_id)
    verificar_acceso_proveedor(current, data.proveedor_id)
    try:
        guia = await guia_remision_repo.crear(db, data)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El número de guía ya existe para este proveedor"
        )

    guia = await guia_remision_repo.get_con_detalle(db, guia.guia_remision_id)
    return _build_detail(guia)


@router.post(
    "/{guia_remision_id}/detalle", response_model=GuiaRemisionDetalleOut, status_code=status.HTTP_201_CREATED
)
async def agregar_detalle_guia(
    guia_remision_id: int,
    data: GuiaRemisionDetalleIn,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> GuiaRemisionDetalleOut:
    guia = await db.get(GuiaRemision, guia_remision_id)
    if guia is not None:
        verificar_acceso_almacen(current, guia.almacen_destino_id)
        verificar_acceso_proveedor(current, guia.proveedor_id)

    try:
        detalle = await guia_remision_repo.agregar_detalle(db, guia_remision_id, data)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return GuiaRemisionDetalleOut.from_model(detalle)
