from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.catalogos import Producto


class CRUDProducto(CRUDBase[Producto]):
    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        categoria: str | None = None,
        estado: str | None = "ACTIVO",
        buscar: str | None = None,
    ) -> tuple[list[Producto], int]:
        stmt = select(Producto)
        if categoria is not None:
            stmt = stmt.where(Producto.categoria == categoria)
        if estado is not None:
            stmt = stmt.where(Producto.estado == estado)
        if buscar:
            like = f"%{buscar}%"
            stmt = stmt.where((Producto.nombre.ilike(like)) | (Producto.codigo.ilike(like)))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Producto.producto_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Producto.nombre).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total


producto_repo = CRUDProducto(Producto)
