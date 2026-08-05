from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.organizacion import UbicacionInterna


class CRUDUbicacionInterna(CRUDBase[UbicacionInterna]):
    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        almacen_id: int | None = None,
        almacen_ids: list[int] | None = None,
    ) -> tuple[list[UbicacionInterna], int]:
        stmt = select(UbicacionInterna)
        if almacen_id is not None:
            stmt = stmt.where(UbicacionInterna.almacen_id == almacen_id)
        if almacen_ids is not None:
            stmt = stmt.where(UbicacionInterna.almacen_id.in_(almacen_ids))

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(UbicacionInterna.ubicacion_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(UbicacionInterna.almacen_id, UbicacionInterna.zona).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total


ubicacion_repo = CRUDUbicacionInterna(UbicacionInterna)
