from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.crud.stock import obtener_o_crear_stock, registrar_movimiento
from app.models.inventario import AjusteInventario, InventarioFisico, InventarioFisicoDetalle
from app.schemas.inventario import InventarioFisicoCreate

EPS = 1e-6


class CRUDInventarioFisico(CRUDBase[InventarioFisico]):
    async def get_con_detalle(self, db: AsyncSession, inventario_fisico_id: int) -> InventarioFisico | None:
        stmt = (
            select(InventarioFisico)
            .where(InventarioFisico.inventario_fisico_id == inventario_fisico_id)
            .options(selectinload(InventarioFisico.detalle).selectinload(InventarioFisicoDetalle.producto))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        almacen_id: int | None = None,
        almacen_ids: list[int] | None = None,
        estado: str | None = None,
    ) -> tuple[list[InventarioFisico], int]:
        stmt = select(InventarioFisico)
        if almacen_id is not None:
            stmt = stmt.where(InventarioFisico.almacen_id == almacen_id)
        if almacen_ids is not None:
            stmt = stmt.where(InventarioFisico.almacen_id.in_(almacen_ids))
        if estado is not None:
            stmt = stmt.where(InventarioFisico.estado == estado)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(InventarioFisico.inventario_fisico_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(InventarioFisico.fecha_conteo.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear(self, db: AsyncSession, data: InventarioFisicoCreate, responsable_id: int) -> InventarioFisico:
        inventario = InventarioFisico(
            almacen_id=data.almacen_id, fecha_conteo=data.fecha_conteo, responsable_id=responsable_id
        )
        db.add(inventario)
        await db.flush()

        for linea in data.detalle:
            stock = await obtener_o_crear_stock(db, data.almacen_id, linea.producto_id)
            db.add(
                InventarioFisicoDetalle(
                    inventario_fisico_id=inventario.inventario_fisico_id,
                    producto_id=linea.producto_id,
                    stock_sistema=stock.stock_fisico,  # RN: foto del sistema, nunca lo manda el cliente
                    stock_contado=linea.stock_contado,
                )
            )

        await db.flush()
        return inventario

    async def cerrar(self, db: AsyncSession, inventario: InventarioFisico, responsable_id: int) -> InventarioFisico:
        """Genera un AjusteInventario automático por cada línea con diferencia
        != 0 y aplica el movimiento de stock correspondiente."""
        if inventario.estado != "EN_PROCESO":
            raise ValueError(f"El inventario físico ya está {inventario.estado}")

        for detalle in inventario.detalle:
            if abs(detalle.diferencia) <= EPS:
                continue

            ajuste = AjusteInventario(
                almacen_id=inventario.almacen_id,
                producto_id=detalle.producto_id,
                cantidad_ajuste=detalle.diferencia,
                motivo=f"Inventario físico #{inventario.inventario_fisico_id}",
                responsable_id=responsable_id,
            )
            db.add(ajuste)
            await db.flush()

            await registrar_movimiento(
                db,
                almacen_id=inventario.almacen_id,
                producto_id=detalle.producto_id,
                tipo_movimiento="INVENTARIO_AJUSTE",
                referencia_tipo="inventario_fisico",
                referencia_id=inventario.inventario_fisico_id,
                cantidad=detalle.diferencia,
                registrado_por_id=responsable_id,
            )
            detalle.ajuste_generado_id = ajuste.ajuste_id

        inventario.estado = "CERRADO"
        await db.flush()
        return inventario


inventario_fisico_repo = CRUDInventarioFisico(InventarioFisico)
