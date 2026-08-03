from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.compras import AutorizacionExcedente, OrdenCompra, OrdenCompraDetalle, OrdenCompraDistribucion
from app.models.contratos import Contrato, ProductoContratado
from app.schemas.compra import OrdenCompraCreate

EPS = 1e-6

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "EMITIDA": {"ANULADA", "CERRADO", "PENALIZADO"},
    # CERRADO/PENALIZADO los fija crud/informe_conformidad.py::cerrar_orden_compra
    # (Módulo 5) tras evaluar las actas de observación de la OC.
    "ANULADA": set(),
    "CERRADO": set(),
    "PENALIZADO": set(),
}


class CRUDOrdenCompra(CRUDBase[OrdenCompra]):
    async def get_con_detalle(self, db: AsyncSession, orden_compra_id: int) -> OrdenCompra | None:
        stmt = (
            select(OrdenCompra)
            .where(OrdenCompra.orden_compra_id == orden_compra_id)
            .options(
                selectinload(OrdenCompra.detalle).selectinload(OrdenCompraDetalle.producto_contratado)
                .selectinload(ProductoContratado.producto),
                selectinload(OrdenCompra.detalle).selectinload(OrdenCompraDetalle.distribucion)
                .selectinload(OrdenCompraDistribucion.almacen),
                selectinload(OrdenCompra.detalle).selectinload(OrdenCompraDetalle.autorizaciones_excedente),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        contrato_id: int | None = None,
        estado: str | None = None,
        buscar: str | None = None,
    ) -> tuple[list[OrdenCompra], int]:
        stmt = select(OrdenCompra)
        if contrato_id is not None:
            stmt = stmt.where(OrdenCompra.contrato_id == contrato_id)
        if estado is not None:
            stmt = stmt.where(OrdenCompra.estado == estado)
        if buscar:
            stmt = stmt.where(OrdenCompra.numero_oc.ilike(f"%{buscar}%"))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(OrdenCompra.orden_compra_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(OrdenCompra.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear(self, db: AsyncSession, data: OrdenCompraCreate, responsable_id: int) -> OrdenCompra:
        contrato = await db.get(Contrato, data.contrato_id)
        if contrato is None:
            raise ValueError("El contrato indicado no existe")
        if contrato.estado != "VIGENTE":
            raise ValueError("Solo se pueden emitir órdenes de compra sobre contratos en estado VIGENTE")

        oc = OrdenCompra(
            numero_oc=data.numero_oc,
            contrato_id=data.contrato_id,
            periodo_mes=data.periodo_mes,
            responsable_id=responsable_id,
        )
        db.add(oc)
        await db.flush()

        for linea in data.detalle:
            producto_contratado = await db.get(ProductoContratado, linea.producto_contratado_id)
            if producto_contratado is None or producto_contratado.contrato_id != data.contrato_id:
                raise ValueError("El producto contratado indicado no pertenece a este contrato")

            precio = producto_contratado.precio_unitario  # RN-09: nunca viene del body
            monto = linea.cantidad_solicitada * precio

            if linea.cantidad_solicitada - producto_contratado.saldo_fisico > EPS:
                raise ValueError(
                    f"RN-01: la cantidad solicitada ({linea.cantidad_solicitada}) excede el saldo "
                    f"físico disponible ({producto_contratado.saldo_fisico}) del producto contratado "
                    f"#{producto_contratado.producto_contratado_id}"
                )
            if monto - producto_contratado.saldo_monetario > EPS:
                raise ValueError(
                    f"RN-01: el monto ({monto:.2f}) excede el saldo monetario disponible "
                    f"({producto_contratado.saldo_monetario:.2f}) del producto contratado "
                    f"#{producto_contratado.producto_contratado_id}"
                )

            suma_distribucion = sum(d.cantidad_distribuida for d in linea.distribucion)
            if abs(suma_distribucion - linea.cantidad_solicitada) > EPS:
                raise ValueError(
                    f"RN-15: la suma distribuida entre almacenes ({suma_distribucion}) debe igualar "
                    f"la cantidad solicitada ({linea.cantidad_solicitada})"
                )

            detalle = OrdenCompraDetalle(
                orden_compra_id=oc.orden_compra_id,
                producto_contratado_id=producto_contratado.producto_contratado_id,
                cantidad_solicitada=linea.cantidad_solicitada,
                precio_unitario_aplicado=precio,
            )
            db.add(detalle)
            await db.flush()

            for d in linea.distribucion:
                db.add(
                    OrdenCompraDistribucion(
                        orden_compra_detalle_id=detalle.orden_compra_detalle_id,
                        almacen_id=d.almacen_id,
                        cantidad_distribuida=d.cantidad_distribuida,
                    )
                )

            # RN-01/RN-19: descuenta el saldo GLOBAL reservado (no consumido aún,
            # ver docs sección 4.3) del producto contratado.
            producto_contratado.saldo_fisico -= linea.cantidad_solicitada
            producto_contratado.saldo_monetario -= monto

        await db.flush()
        return oc

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    async def anular(self, db: AsyncSession, orden_compra: OrdenCompra) -> None:
        """Revierte el saldo reservado en cada producto_contratado. Se bloquea si
        ya se registró alguna entrega (guía) sobre cualquier línea de la OC."""
        self.validar_transicion(orden_compra.estado, "ANULADA")

        for detalle in orden_compra.detalle:
            if detalle.cantidad_ingresada_acumulada > 0:
                raise ValueError(
                    "No se puede anular: ya se registraron entregas (guías) sobre esta orden de compra"
                )

        for detalle in orden_compra.detalle:
            producto_contratado = detalle.producto_contratado
            producto_contratado.saldo_fisico += detalle.cantidad_solicitada
            producto_contratado.saldo_monetario += detalle.cantidad_solicitada * detalle.precio_unitario_aplicado

        orden_compra.estado = "ANULADA"

    async def autorizar_excedente(
        self,
        db: AsyncSession,
        orden_compra_detalle_id: int,
        cantidad_excedente: float,
        justificacion: str,
        autorizado_por_id: int,
    ) -> AutorizacionExcedente:
        """RN-03: autoriza que la línea reciba hasta cantidad_excedente por
        encima de cantidad_solicitada (ver crud/guia_remision.py::_registrar_linea)."""
        ocd = await db.get(OrdenCompraDetalle, orden_compra_detalle_id)
        if ocd is None:
            raise ValueError("La línea de orden de compra indicada no existe")

        autorizacion = AutorizacionExcedente(
            orden_compra_detalle_id=orden_compra_detalle_id,
            cantidad_excedente=cantidad_excedente,
            justificacion=justificacion,
            autorizado_por_id=autorizado_por_id,
        )
        db.add(autorizacion)
        await db.flush()
        return autorizacion


orden_compra_repo = CRUDOrdenCompra(OrdenCompra)
