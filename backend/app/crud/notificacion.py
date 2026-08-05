from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.notificacion import Notificacion


class CRUDNotificacion(CRUDBase[Notificacion]):
    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        leida: bool | None = None,
    ) -> tuple[list[Notificacion], int]:
        stmt = select(Notificacion)
        if leida is not None:
            stmt = stmt.where(Notificacion.leida == leida)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Notificacion.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def existe_no_leida(self, db: AsyncSession, tipo: str, referencia_id: int) -> bool:
        """Dedup del job de RN-12 (core/jobs.py): mientras una alerta siga
        sin marcarse leída, no se vuelve a notificar cada día."""
        stmt = select(func.count()).select_from(Notificacion).where(
            Notificacion.tipo == tipo,
            Notificacion.referencia_id == referencia_id,
            Notificacion.leida.is_(False),
        )
        return (await db.execute(stmt)).scalar_one() > 0

    async def marcar_leida(self, db: AsyncSession, notificacion_id: int) -> Notificacion | None:
        notificacion = await self.get(db, notificacion_id)
        if notificacion is None:
            return None
        notificacion.leida = True
        await db.flush()
        return notificacion


notificacion_repo = CRUDNotificacion(Notificacion)
