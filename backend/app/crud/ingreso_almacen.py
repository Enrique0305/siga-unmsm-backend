from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.crud.stock import registrar_bin_card, registrar_movimiento
from app.models.compras import GuiaRemision, GuiaRemisionDetalle, OrdenCompraDetalle
from app.models.contratos import ProductoContratado
from app.models.inspeccion import InspeccionDetalle
from app.models.inventario import IngresoAlmacen, IngresoAlmacenDetalle
from app.schemas.inventario import IngresoAlmacenCreate

EPS = 1e-6


class CRUDIngresoAlmacen(CRUDBase[IngresoAlmacen]):
    async def get_con_detalle(self, db: AsyncSession, ingreso_almacen_id: int) -> IngresoAlmacen | None:
        stmt = (
            select(IngresoAlmacen)
            .where(IngresoAlmacen.ingreso_almacen_id == ingreso_almacen_id)
            .options(selectinload(IngresoAlmacen.detalle).selectinload(IngresoAlmacenDetalle.producto))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        almacen_id: int | None = None,
        almacen_ids: list[int] | None = None,
        guia_remision_id: int | None = None,
    ) -> tuple[list[IngresoAlmacen], int]:
        stmt = select(IngresoAlmacen)
        if almacen_id is not None:
            stmt = stmt.where(IngresoAlmacen.almacen_id == almacen_id)
        if almacen_ids is not None:
            stmt = stmt.where(IngresoAlmacen.almacen_id.in_(almacen_ids))
        if guia_remision_id is not None:
            stmt = stmt.where(IngresoAlmacen.guia_remision_id == guia_remision_id)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(IngresoAlmacen.ingreso_almacen_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(IngresoAlmacen.fecha_ingreso.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def _ids_ya_ingresadas(self, db: AsyncSession) -> set[int]:
        stmt = select(IngresoAlmacenDetalle.inspeccion_detalle_id)
        return set((await db.execute(stmt)).scalars().all())

    async def crear(self, db: AsyncSession, data: IngresoAlmacenCreate, almacenero_id: int) -> IngresoAlmacen:
        guia = await db.get(GuiaRemision, data.guia_remision_id)
        if guia is None:
            raise ValueError("La guía de remisión indicada no existe")

        ingreso = IngresoAlmacen(
            numero_ingreso=data.numero_ingreso,
            guia_remision_id=guia.guia_remision_id,
            almacen_id=guia.almacen_destino_id,  # RN: nunca lo manda el cliente
            almacenero_id=almacenero_id,
        )
        db.add(ingreso)
        await db.flush()

        ya_ingresadas = await self._ids_ya_ingresadas(db)

        for linea in data.detalle:
            if linea.inspeccion_detalle_id in ya_ingresadas:
                raise ValueError(f"La línea de inspección #{linea.inspeccion_detalle_id} ya fue ingresada a almacén")

            stmt = (
                select(InspeccionDetalle)
                .where(InspeccionDetalle.inspeccion_detalle_id == linea.inspeccion_detalle_id)
                .options(
                    selectinload(InspeccionDetalle.inspeccion),
                    selectinload(InspeccionDetalle.guia_remision_detalle)
                    .selectinload(GuiaRemisionDetalle.orden_compra_detalle)
                    .selectinload(OrdenCompraDetalle.producto_contratado)
                    .selectinload(ProductoContratado.producto),
                )
            )
            inspeccion_detalle = (await db.execute(stmt)).scalar_one_or_none()
            if inspeccion_detalle is None:
                raise ValueError(f"La línea de inspección #{linea.inspeccion_detalle_id} no existe")
            if inspeccion_detalle.inspeccion.guia_remision_id != guia.guia_remision_id:
                raise ValueError(
                    f"La línea de inspección #{linea.inspeccion_detalle_id} no pertenece a esta guía de remisión"
                )
            if abs(linea.cantidad_ingresada - inspeccion_detalle.cantidad_conforme) > EPS:
                raise ValueError(
                    f"RN-04: la cantidad a ingresar ({linea.cantidad_ingresada}) debe igualar la cantidad "
                    f"conforme ({inspeccion_detalle.cantidad_conforme}) de la línea de inspección "
                    f"#{linea.inspeccion_detalle_id}"
                )

            orden_compra_detalle = inspeccion_detalle.guia_remision_detalle.orden_compra_detalle
            producto = orden_compra_detalle.producto_contratado.producto
            costo_unitario = orden_compra_detalle.precio_unitario_aplicado

            detalle = IngresoAlmacenDetalle(
                ingreso_almacen_id=ingreso.ingreso_almacen_id,
                inspeccion_detalle_id=linea.inspeccion_detalle_id,
                producto_id=producto.producto_id,
                cantidad_ingresada=linea.cantidad_ingresada,
                costo_unitario=costo_unitario,
                ubicacion_id=linea.ubicacion_id,
            )
            db.add(detalle)
            ya_ingresadas.add(linea.inspeccion_detalle_id)

            await registrar_movimiento(
                db,
                almacen_id=ingreso.almacen_id,
                producto_id=producto.producto_id,
                tipo_movimiento="INGRESO",
                referencia_tipo="ingreso_almacen",
                referencia_id=ingreso.ingreso_almacen_id,
                cantidad=linea.cantidad_ingresada,
                registrado_por_id=almacenero_id,
                costo_unitario_entrante=costo_unitario,
            )

            if linea.ubicacion_id is not None:
                await registrar_bin_card(
                    db,
                    almacen_id=ingreso.almacen_id,
                    producto_id=producto.producto_id,
                    ubicacion_id=linea.ubicacion_id,
                    tipo_movimiento="INGRESO",
                    referencia_tipo="ingreso_almacen",
                    referencia_id=ingreso.ingreso_almacen_id,
                    cantidad=linea.cantidad_ingresada,
                )

        await db.flush()
        return ingreso


ingreso_almacen_repo = CRUDIngresoAlmacen(IngresoAlmacen)
