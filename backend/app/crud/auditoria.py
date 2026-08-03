from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.auditoria import AuditoriaLog


class CRUDAuditoriaLog(CRUDBase[AuditoriaLog]):
    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        entidad: str | None = None,
        entidad_id: int | None = None,
        usuario_id: int | None = None,
    ) -> tuple[list[AuditoriaLog], int]:
        stmt = select(AuditoriaLog)
        if entidad is not None:
            stmt = stmt.where(AuditoriaLog.entidad == entidad)
        if entidad_id is not None:
            stmt = stmt.where(AuditoriaLog.entidad_id == entidad_id)
        if usuario_id is not None:
            stmt = stmt.where(AuditoriaLog.usuario_id == usuario_id)

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(AuditoriaLog.auditoria_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(AuditoriaLog.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total


auditoria_repo = CRUDAuditoriaLog(AuditoriaLog)
