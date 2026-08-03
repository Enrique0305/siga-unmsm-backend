from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.orden_compra import orden_compra_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.compra import OrdenCompraCreate, OrdenCompraDetailOut, OrdenCompraEstadoUpdate, OrdenCompraOut

router = APIRouter(prefix="/ordenes-compra", tags=["Órdenes de compra"])

# "[Logística] genera Orden de Compra" (docs sección 4.3)
ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[OrdenCompraOut])
async def listar_ordenes_compra(
    page: int = 1,
    page_size: int = 20,
    contrato_id: int | None = None,
    estado: str | None = None,
    buscar: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[OrdenCompraOut]:
    items, total = await orden_compra_repo.list_filtrado(
        db, page=page, page_size=page_size, contrato_id=contrato_id, estado=estado, buscar=buscar
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{orden_compra_id}", response_model=OrdenCompraDetailOut)
async def obtener_orden_compra(
    orden_compra_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> OrdenCompraDetailOut:
    oc = await orden_compra_repo.get_con_detalle(db, orden_compra_id)
    if oc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada")
    return OrdenCompraDetailOut.from_model(oc)


@router.post("", response_model=OrdenCompraDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_orden_compra(
    data: OrdenCompraCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> OrdenCompraDetailOut:
    """RN-01 (saldo suficiente) · RN-09 (precio del contrato, no editable) ·
    RN-15 (distribución multialmacén = cantidad solicitada) · RN-19 (saldo
    GLOBAL, no por almacén)."""
    try:
        oc = await orden_compra_repo.crear(db, data, responsable_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El número de OC ya existe, o hay un almacén repetido en la distribución de una línea",
        )

    oc = await orden_compra_repo.get_con_detalle(db, oc.orden_compra_id)
    return OrdenCompraDetailOut.from_model(oc)


@router.patch("/{orden_compra_id}/estado", response_model=OrdenCompraOut)
async def cambiar_estado_orden_compra(
    orden_compra_id: int,
    data: OrdenCompraEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> OrdenCompraOut:
    """Única transición soportada: EMITIDA -> ANULADA, que revierte el saldo
    reservado del producto contratado. Se bloquea si ya hubo entregas
    (guías) registradas sobre la OC."""
    oc = await orden_compra_repo.get_con_detalle(db, orden_compra_id)
    if oc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada")

    try:
        if data.estado == "ANULADA":
            await orden_compra_repo.anular(db, oc)
        else:
            orden_compra_repo.validar_transicion(oc.estado, data.estado)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.commit()
    await db.refresh(oc)
    return oc
