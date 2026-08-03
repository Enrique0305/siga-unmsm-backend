from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.compras import OrdenCompra
from app.models.pagos import InformeConformidadPago, Penalidad
from app.schemas.pagos import PenalidadCreate


class CRUDPenalidad(CRUDBase[Penalidad]):
    async def list_filtrado(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, orden_compra_id: int | None = None
    ) -> tuple[list[Penalidad], int]:
        stmt = select(Penalidad)
        if orden_compra_id is not None:
            stmt = stmt.where(Penalidad.orden_compra_id == orden_compra_id)

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Penalidad.penalidad_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Penalidad.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear_manual(self, db: AsyncSession, data: PenalidadCreate) -> Penalidad:
        """Penalidad no ligada a una observación de calidad (ej. atraso de
        entrega). Bloqueada si la OC ya tiene un informe de conformidad
        generado, para no descuadrar montos ya reportados a pago."""
        if await db.get(OrdenCompra, data.orden_compra_id) is None:
            raise ValueError("La orden de compra indicada no existe")

        stmt = select(InformeConformidadPago.informe_id).where(
            InformeConformidadPago.orden_compra_id == data.orden_compra_id
        )
        if (await db.execute(stmt)).scalar_one_or_none() is not None:
            raise ValueError(
                "No se puede registrar la penalidad: ya se generó el informe de conformidad de esta OC"
            )

        penalidad = Penalidad(
            orden_compra_id=data.orden_compra_id,
            monto_penalidad=data.monto_penalidad,
            motivo=data.motivo,
        )
        db.add(penalidad)
        await db.flush()
        return penalidad


penalidad_repo = CRUDPenalidad(Penalidad)
