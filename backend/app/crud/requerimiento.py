from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.planificacion import RequerimientoAnual, RequerimientoAnualDetalle
from app.schemas.requerimiento import RequerimientoAnualCreate

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "BORRADOR": {"EN_REVISION"},
    "EN_REVISION": {"APROBADO", "BORRADOR"},
    "APROBADO": {"VIGENTE"},
    "VIGENTE": set(),
}


class CRUDRequerimientoAnual(CRUDBase[RequerimientoAnual]):
    async def get_con_detalle(self, db: AsyncSession, requerimiento_anual_id: int) -> RequerimientoAnual | None:
        stmt = (
            select(RequerimientoAnual)
            .where(RequerimientoAnual.requerimiento_anual_id == requerimiento_anual_id)
            .options(selectinload(RequerimientoAnual.detalle).selectinload(RequerimientoAnualDetalle.producto))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        estado: str | None = None,
        racion_anual_id: int | None = None,
    ) -> tuple[list[RequerimientoAnual], int]:
        stmt = select(RequerimientoAnual)
        if estado is not None:
            stmt = stmt.where(RequerimientoAnual.estado == estado)
        if racion_anual_id is not None:
            stmt = stmt.where(RequerimientoAnual.racion_anual_id == racion_anual_id)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(RequerimientoAnual.requerimiento_anual_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(RequerimientoAnual.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear_con_detalle(self, db: AsyncSession, data: RequerimientoAnualCreate) -> RequerimientoAnual:
        requerimiento = RequerimientoAnual(
            racion_anual_id=data.racion_anual_id,
            presupuesto_referencial_total=data.presupuesto_referencial_total,
        )
        db.add(requerimiento)
        await db.flush()

        for linea in data.detalle:
            db.add(
                RequerimientoAnualDetalle(
                    requerimiento_anual_id=requerimiento.requerimiento_anual_id,
                    **linea.model_dump(),
                )
            )
        await db.flush()
        return requerimiento

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    def aplicar_transicion(self, requerimiento: RequerimientoAnual, estado_nuevo: str, aprobado_por_id: int) -> None:
        requerimiento.estado = estado_nuevo
        if estado_nuevo == "APROBADO":
            requerimiento.aprobado_por_id = aprobado_por_id
            requerimiento.aprobado_en = datetime.now(timezone.utc)


requerimiento_repo = CRUDRequerimientoAnual(RequerimientoAnual)
