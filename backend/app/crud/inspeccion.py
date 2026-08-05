from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.compras import GuiaRemision, GuiaRemisionDetalle, OrdenCompraDetalle
from app.models.contratos import ProductoContratado
from app.models.inspeccion import Inspeccion, InspeccionDetalle
from app.schemas.inspeccion import InspeccionCreate

EPS = 1e-6


class CRUDInspeccion(CRUDBase[Inspeccion]):
    async def get_con_detalle(self, db: AsyncSession, inspeccion_id: int) -> Inspeccion | None:
        stmt = (
            select(Inspeccion)
            .where(Inspeccion.inspeccion_id == inspeccion_id)
            .options(
                selectinload(Inspeccion.detalle)
                .selectinload(InspeccionDetalle.guia_remision_detalle)
                .selectinload(GuiaRemisionDetalle.orden_compra_detalle)
                .selectinload(OrdenCompraDetalle.producto_contratado)
                .selectinload(ProductoContratado.producto),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        guia_remision_id: int | None = None,
        almacen_ids: list[int] | None = None,
    ) -> tuple[list[Inspeccion], int]:
        stmt = select(Inspeccion)
        if guia_remision_id is not None:
            stmt = stmt.where(Inspeccion.guia_remision_id == guia_remision_id)
        if almacen_ids is not None:
            stmt = stmt.join(GuiaRemision, Inspeccion.guia_remision_id == GuiaRemision.guia_remision_id).where(
                GuiaRemision.almacen_destino_id.in_(almacen_ids)
            )

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Inspeccion.inspeccion_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Inspeccion.fecha_inspeccion.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def _ids_ya_inspeccionadas(self, db: AsyncSession, guia_remision_id: int) -> set[int]:
        stmt = (
            select(InspeccionDetalle.guia_remision_detalle_id)
            .join(Inspeccion, InspeccionDetalle.inspeccion_id == Inspeccion.inspeccion_id)
            .where(Inspeccion.guia_remision_id == guia_remision_id)
        )
        return set((await db.execute(stmt)).scalars().all())

    async def _hay_linea_observada(self, db: AsyncSession, guia_remision_id: int) -> bool:
        stmt = (
            select(func.count())
            .select_from(InspeccionDetalle)
            .join(Inspeccion, InspeccionDetalle.inspeccion_id == Inspeccion.inspeccion_id)
            .where(Inspeccion.guia_remision_id == guia_remision_id, InspeccionDetalle.resultado == "OBSERVADO")
        )
        return (await db.execute(stmt)).scalar_one() > 0

    async def crear(self, db: AsyncSession, data: InspeccionCreate, inspector_id: int) -> Inspeccion:
        stmt = (
            select(GuiaRemision)
            .where(GuiaRemision.guia_remision_id == data.guia_remision_id)
            .options(selectinload(GuiaRemision.detalle))
        )
        guia = (await db.execute(stmt)).scalar_one_or_none()
        if guia is None:
            raise ValueError("La guía de remisión indicada no existe")

        detalle_por_id = {d.guia_remision_detalle_id: d for d in guia.detalle}
        ya_inspeccionadas = await self._ids_ya_inspeccionadas(db, guia.guia_remision_id)

        inspeccion = Inspeccion(guia_remision_id=guia.guia_remision_id, inspector_id=inspector_id)
        db.add(inspeccion)
        await db.flush()

        for linea in data.detalle:
            grd = detalle_por_id.get(linea.guia_remision_detalle_id)
            if grd is None:
                raise ValueError(
                    f"La línea de guía #{linea.guia_remision_detalle_id} no pertenece a esta guía de remisión"
                )
            if linea.guia_remision_detalle_id in ya_inspeccionadas:
                raise ValueError(f"La línea de guía #{linea.guia_remision_detalle_id} ya fue inspeccionada")

            suma = linea.cantidad_conforme + linea.cantidad_observada
            if abs(suma - grd.cantidad_entregada) > EPS:
                raise ValueError(
                    f"La suma conforme + observada ({suma}) debe igualar la cantidad entregada "
                    f"({grd.cantidad_entregada}) de la línea de guía #{linea.guia_remision_detalle_id}"
                )

            resultado = "OBSERVADO" if linea.cantidad_observada > EPS else "CONFORME"
            db.add(
                InspeccionDetalle(
                    inspeccion_id=inspeccion.inspeccion_id,
                    guia_remision_detalle_id=linea.guia_remision_detalle_id,
                    cantidad_conforme=linea.cantidad_conforme,
                    cantidad_observada=linea.cantidad_observada,
                    resultado=resultado,
                )
            )
            ya_inspeccionadas.add(linea.guia_remision_detalle_id)

        await db.flush()

        # Recalcula guia_remision.estado (PENDIENTE -> PARCIAL -> CONFORME/OBSERVADO)
        # contra el total de líneas de la guía, no solo el lote recién inspeccionado.
        if len(ya_inspeccionadas) < len(guia.detalle):
            guia.estado = "PARCIAL"
        else:
            guia.estado = "OBSERVADO" if await self._hay_linea_observada(db, guia.guia_remision_id) else "CONFORME"

        return inspeccion


inspeccion_repo = CRUDInspeccion(Inspeccion)
