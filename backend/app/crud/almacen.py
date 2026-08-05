from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.organizacion import Almacen


class CRUDAlmacen(CRUDBase[Almacen]):
    async def get_by_codigo(self, db: AsyncSession, codigo: str) -> Almacen | None:
        stmt = select(Almacen).where(Almacen.codigo == codigo)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        estado: str | None = None,
        almacen_ids: list[int] | None = None,
    ) -> tuple[list[Almacen], int]:
        """RN-20 en lecturas (Sesión 15): reemplaza el filtrado post-fetch en
        Python que rompía `total`/paginación para roles restringidos —
        `almacen_ids` (IN) se aplica a nivel SQL, antes de paginar."""
        stmt = select(Almacen)
        if estado is not None:
            stmt = stmt.where(Almacen.estado == estado)
        if almacen_ids is not None:
            stmt = stmt.where(Almacen.almacen_id.in_(almacen_ids))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Almacen.almacen_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total


almacen_repo = CRUDAlmacen(Almacen)
