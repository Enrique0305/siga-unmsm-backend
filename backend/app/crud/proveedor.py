from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.contratos import Proveedor


class CRUDProveedor(CRUDBase[Proveedor]):
    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        estado: str | None = "ACTIVO",
        buscar: str | None = None,
    ) -> tuple[list[Proveedor], int]:
        stmt = select(Proveedor)
        if estado is not None:
            stmt = stmt.where(Proveedor.estado == estado)
        if buscar:
            like = f"%{buscar}%"
            stmt = stmt.where((Proveedor.razon_social.ilike(like)) | (Proveedor.ruc.ilike(like)))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Proveedor.proveedor_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Proveedor.razon_social).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total


proveedor_repo = CRUDProveedor(Proveedor)
