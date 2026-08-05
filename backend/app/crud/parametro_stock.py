from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogos import Producto
from app.models.inventario import AlmacenProductoParametro
from app.models.organizacion import Almacen
from app.schemas.inventario import AlmacenProductoParametroIn


async def list_filtrado(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    almacen_ids: list[int] | None = None,
    producto_id: int | None = None,
) -> tuple[list[AlmacenProductoParametro], int]:
    stmt = select(AlmacenProductoParametro)
    if almacen_id is not None:
        stmt = stmt.where(AlmacenProductoParametro.almacen_id == almacen_id)
    if almacen_ids is not None:
        stmt = stmt.where(AlmacenProductoParametro.almacen_id.in_(almacen_ids))
    if producto_id is not None:
        stmt = stmt.where(AlmacenProductoParametro.producto_id == producto_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(AlmacenProductoParametro.almacen_id, AlmacenProductoParametro.producto_id)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def upsert(db: AsyncSession, data: AlmacenProductoParametroIn) -> AlmacenProductoParametro:
    if await db.get(Almacen, data.almacen_id) is None:
        raise ValueError("El almacén indicado no existe")
    if await db.get(Producto, data.producto_id) is None:
        raise ValueError("El producto indicado no existe")

    existente = await db.get(AlmacenProductoParametro, (data.almacen_id, data.producto_id))
    if existente is not None:
        existente.stock_minimo = data.stock_minimo
        await db.flush()
        return existente

    parametro = AlmacenProductoParametro(**data.model_dump())
    db.add(parametro)
    await db.flush()
    return parametro


async def eliminar(db: AsyncSession, almacen_id: int, producto_id: int) -> bool:
    parametro = await db.get(AlmacenProductoParametro, (almacen_id, producto_id))
    if parametro is None:
        return False
    await db.delete(parametro)
    await db.flush()
    return True
