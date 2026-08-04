from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.pedido_semanal import pedido_semanal_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.compra import PedidoSemanalCreate, PedidoSemanalOut

router = APIRouter(prefix="/pedidos-semanales", tags=["Pedidos semanales"])

# "[Logística/Nutrición] genera Pedido Semanal a partir del Menú Quincenal vigente"
ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL", "NUTRICION")


@router.get("", response_model=Page[PedidoSemanalOut])
async def listar_pedidos_semanales(
    page: int = 1,
    page_size: int = 20,
    orden_compra_id: int | None = None,
    almacen_id: int | None = None,
    menu_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[PedidoSemanalOut]:
    items, total = await pedido_semanal_repo.list_filtrado(
        db, page=page, page_size=page_size, orden_compra_id=orden_compra_id, almacen_id=almacen_id, menu_id=menu_id
    )
    return Page(
        items=[PedidoSemanalOut.from_model(p) for p in items], total=total, page=page, page_size=page_size
    )


@router.get("/{pedido_semanal_id}", response_model=PedidoSemanalOut)
async def obtener_pedido_semanal(
    pedido_semanal_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> PedidoSemanalOut:
    pedido = await pedido_semanal_repo.get_con_relaciones(db, pedido_semanal_id)
    if pedido is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pedido semanal no encontrado")
    return PedidoSemanalOut.from_model(pedido)


@router.post("", response_model=PedidoSemanalOut, status_code=status.HTTP_201_CREATED)
async def crear_pedido_semanal(
    data: PedidoSemanalCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> PedidoSemanalOut:
    """RN-16: único por combinación (menú, almacén, semana_inicio)."""
    verificar_acceso_almacen(current, data.almacen_id)
    try:
        pedido = await pedido_semanal_repo.crear(db, data)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un pedido semanal para esa combinación de menú, almacén y semana (RN-16)",
        )

    return PedidoSemanalOut.from_model(pedido)
