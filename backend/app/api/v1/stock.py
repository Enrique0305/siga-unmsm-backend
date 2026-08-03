from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.crud.stock import list_kardex, list_stock
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.inventario import KardexMovimientoOut, StockAlmacenProductoOut

router = APIRouter(tags=["Stock y kardex"])


@router.get("/stock-almacen", response_model=Page[StockAlmacenProductoOut])
async def listar_stock(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    producto_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[StockAlmacenProductoOut]:
    items, total = await list_stock(db, page=page, page_size=page_size, almacen_id=almacen_id, producto_id=producto_id)
    return Page(
        items=[StockAlmacenProductoOut.from_model(s) for s in items], total=total, page=page, page_size=page_size
    )


@router.get("/kardex", response_model=Page[KardexMovimientoOut])
async def listar_kardex(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    producto_id: int | None = None,
    tipo_movimiento: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[KardexMovimientoOut]:
    items, total = await list_kardex(
        db, page=page, page_size=page_size, almacen_id=almacen_id, producto_id=producto_id, tipo_movimiento=tipo_movimiento
    )
    return Page(
        items=[KardexMovimientoOut.from_model(k) for k in items], total=total, page=page, page_size=page_size
    )
