from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.organizacion import Almacen


class CRUDAlmacen(CRUDBase[Almacen]):
    async def get_by_codigo(self, db: AsyncSession, codigo: str) -> Almacen | None:
        stmt = select(Almacen).where(Almacen.codigo == codigo)
        return (await db.execute(stmt)).scalar_one_or_none()


almacen_repo = CRUDAlmacen(Almacen)
