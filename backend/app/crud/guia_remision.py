from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.compras import GuiaRemision, GuiaRemisionDetalle, OrdenCompra, OrdenCompraDetalle, PedidoSemanal
from app.models.contratos import ProductoContratado, Proveedor
from app.models.organizacion import Almacen
from app.schemas.compra import GuiaRemisionCreate, GuiaRemisionDetalleIn

EPS = 1e-6


class CRUDGuiaRemision(CRUDBase[GuiaRemision]):
    async def get_con_detalle(self, db: AsyncSession, guia_remision_id: int) -> GuiaRemision | None:
        stmt = (
            select(GuiaRemision)
            .where(GuiaRemision.guia_remision_id == guia_remision_id)
            .options(
                selectinload(GuiaRemision.detalle)
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
        orden_compra_id: int | None = None,
        proveedor_id: int | None = None,
        estado: str | None = None,
    ) -> tuple[list[GuiaRemision], int]:
        stmt = select(GuiaRemision)
        if orden_compra_id is not None:
            stmt = stmt.where(GuiaRemision.orden_compra_id == orden_compra_id)
        if proveedor_id is not None:
            stmt = stmt.where(GuiaRemision.proveedor_id == proveedor_id)
        if estado is not None:
            stmt = stmt.where(GuiaRemision.estado == estado)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(GuiaRemision.guia_remision_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(GuiaRemision.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def _registrar_linea(
        self, db: AsyncSession, guia_remision_id: int, orden_compra_id: int, data: GuiaRemisionDetalleIn
    ) -> GuiaRemisionDetalle:
        ocd = await db.get(OrdenCompraDetalle, data.orden_compra_detalle_id)
        if ocd is None or ocd.orden_compra_id != orden_compra_id:
            raise ValueError(
                "La línea de orden de compra indicada no pertenece a la orden de compra de esta guía"
            )
        if data.cantidad_entregada - ocd.saldo_oc > EPS:
            raise ValueError(
                f"RN-03: la cantidad entregada ({data.cantidad_entregada}) excede el saldo pendiente "
                f"({ocd.saldo_oc}) de la línea de OC #{ocd.orden_compra_detalle_id}"
            )

        detalle = GuiaRemisionDetalle(
            guia_remision_id=guia_remision_id,
            orden_compra_detalle=ocd,
            cantidad_entregada=data.cantidad_entregada,
            lote=data.lote,
            fecha_vencimiento=data.fecha_vencimiento,
        )
        db.add(detalle)
        ocd.cantidad_ingresada_acumulada += data.cantidad_entregada
        await db.flush()
        # saldo_oc es GENERATED ALWAYS en MySQL; queda "expirado" tras el UPDATE
        # de cantidad_ingresada_acumulada (ver CLAUDE.md sección 7.3).
        await db.refresh(ocd)
        return detalle

    async def crear(self, db: AsyncSession, data: GuiaRemisionCreate) -> GuiaRemision:
        if await db.get(Proveedor, data.proveedor_id) is None:
            raise ValueError("El proveedor indicado no existe")
        if await db.get(OrdenCompra, data.orden_compra_id) is None:
            raise ValueError("La orden de compra indicada no existe")

        pedido_semanal = await db.get(PedidoSemanal, data.pedido_semanal_id)
        if pedido_semanal is None:
            raise ValueError("El pedido semanal indicado no existe")
        if pedido_semanal.orden_compra_id != data.orden_compra_id:
            raise ValueError("RN-02: el pedido semanal indicado no pertenece a esta orden de compra")

        if await db.get(Almacen, data.almacen_destino_id) is None:
            raise ValueError("El almacén destino indicado no existe")

        guia = GuiaRemision(
            numero_guia=data.numero_guia,
            proveedor_id=data.proveedor_id,
            orden_compra_id=data.orden_compra_id,
            pedido_semanal_id=data.pedido_semanal_id,
            almacen_destino_id=data.almacen_destino_id,
            fecha_entrega=data.fecha_entrega,
        )
        db.add(guia)
        await db.flush()

        for linea in data.detalle:
            await self._registrar_linea(db, guia.guia_remision_id, data.orden_compra_id, linea)

        await db.flush()
        return guia

    async def agregar_detalle(
        self, db: AsyncSession, guia_remision_id: int, data: GuiaRemisionDetalleIn
    ) -> GuiaRemisionDetalle:
        guia = await db.get(GuiaRemision, guia_remision_id)
        if guia is None:
            raise ValueError("La guía de remisión indicada no existe")
        return await self._registrar_linea(db, guia_remision_id, guia.orden_compra_id, data)


guia_remision_repo = CRUDGuiaRemision(GuiaRemision)
