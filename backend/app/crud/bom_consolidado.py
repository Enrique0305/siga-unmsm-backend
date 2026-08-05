from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.requerimiento import requerimiento_repo
from app.models.catalogos import Producto
from app.models.contratos import Contrato, ProductoContratado
from app.models.dosificacion import BomConsolidado, DosificacionDetalle
from app.models.inventario import StockAlmacenProducto
from app.models.planificacion import MenuDia, MenuQuincenal, RacionAnual, RequerimientoAnual
from app.schemas.requerimiento import RequerimientoAnualCreate, RequerimientoAnualDetalleIn


class ServicioBomConsolidado:
    """Consolida la explosión de materiales (Módulo 1A, RN-24) ya calculada por
    día de menú hacia un Requerimiento Anual, cerrando el pipeline descrito en
    el diseño (Menú Quincenal -> BOM -> Requerimiento Anual).

    Límite consciente de esta versión (ver CLAUDE.md sección 10, Sesión 13):
    tipo_periodo fijo en "ANIO" (periodo_inicio/fin = 1 ene / 31 dic del año
    de la ración anual) — la tabla soporta SEMANA/QUINCENA/MES pero no se
    expone esa granularidad todavía (necesitaría selección de rango de
    fechas en el endpoint/UI de consolidación, deuda técnica separada).
    """

    async def generar_y_consolidar(self, db: AsyncSession, racion_anual_id: int) -> RequerimientoAnual:
        racion = await db.get(RacionAnual, racion_anual_id)
        if racion is None:
            raise ValueError("Ración anual no encontrada")

        existentes, _ = await requerimiento_repo.list_filtrado(
            db, page=1, page_size=1, racion_anual_id=racion_anual_id
        )
        if existentes:
            raise ValueError("Ya existe un requerimiento anual generado para esta ración anual")

        stmt = (
            select(
                DosificacionDetalle.almacen_id,
                Producto.producto_id,
                Producto.unidad_id,
                func.sum(DosificacionDetalle.cantidad_bruta_requerida).label("cantidad_total"),
            )
            .join(MenuDia, MenuDia.menu_dia_id == DosificacionDetalle.menu_dia_id)
            .join(MenuQuincenal, MenuQuincenal.menu_id == MenuDia.menu_id)
            .join(Producto, Producto.alimento_id == DosificacionDetalle.alimento_id)
            .where(MenuQuincenal.racion_anual_id == racion_anual_id)
            .group_by(DosificacionDetalle.almacen_id, Producto.producto_id, Producto.unidad_id)
        )
        filas = (await db.execute(stmt)).all()
        if not filas:
            raise ValueError(
                "No hay dosificación calculada para esta ración anual — "
                "calcule la dosificación de al menos un día de menú primero"
            )

        periodo_inicio = date(racion.anio, 1, 1)
        periodo_fin = date(racion.anio, 12, 31)
        almacenes_ids = {f.almacen_id for f in filas}
        productos_ids = {f.producto_id for f in filas}

        # Idempotente: reemplaza cualquier consolidación previa de esta misma
        # ración anual — repetir la consolidación nunca toca las filas de
        # otra ración, aunque sea del mismo año calendario.
        await db.execute(delete(BomConsolidado).where(BomConsolidado.racion_anual_id == racion_anual_id))

        stock_map: dict[tuple[int, int], float] = {}
        stmt_stock = select(StockAlmacenProducto).where(
            StockAlmacenProducto.almacen_id.in_(almacenes_ids),
            StockAlmacenProducto.producto_id.in_(productos_ids),
        )
        for fila_stock in (await db.execute(stmt_stock)).scalars().all():
            # stock_disponible = stock_fisico - stock_comprometido (columna
            # generada, ver models/inventario.py::StockAlmacenProducto) — no
            # stock_fisico a secas, para que la referencia realmente refleje
            # lo disponible (RN-21), como promete el nombre del campo.
            stock_map[(fila_stock.almacen_id, fila_stock.producto_id)] = fila_stock.stock_disponible

        saldo_map: dict[int, float] = {}
        stmt_saldo = (
            select(ProductoContratado.producto_id, func.sum(ProductoContratado.saldo_fisico))
            .join(Contrato, Contrato.contrato_id == ProductoContratado.contrato_id)
            .where(Contrato.estado == "VIGENTE", ProductoContratado.producto_id.in_(productos_ids))
            .group_by(ProductoContratado.producto_id)
        )
        for producto_id, saldo in (await db.execute(stmt_saldo)).all():
            saldo_map[producto_id] = saldo

        totales_por_producto: dict[int, tuple[float, int]] = {}
        for almacen_id, producto_id, unidad_id, cantidad_total in filas:
            stock_ref = stock_map.get((almacen_id, producto_id))
            saldo_ref = saldo_map.get(producto_id)
            # Prioridad: stock físico disponible primero — es la restricción
            # más inmediata (si no está en el almacén ahora, no importa que
            # el contrato tenga saldo; el contrato es la palanca para
            # reponerlo, no para tenerlo ya). RN-28 / diseño línea 212-219.
            if stock_ref is not None and stock_ref < cantidad_total:
                estado = "ALERTA_STOCK"
            elif saldo_ref is None or saldo_ref < cantidad_total:
                estado = "ALERTA_CONTRATO"
            else:
                estado = "SUFICIENTE"
            db.add(
                BomConsolidado(
                    racion_anual_id=racion_anual_id,
                    tipo_periodo="ANIO",
                    periodo_inicio=periodo_inicio,
                    periodo_fin=periodo_fin,
                    almacen_id=almacen_id,
                    producto_id=producto_id,
                    cantidad_requerida_total=round(cantidad_total, 4),
                    stock_disponible_referencia=stock_ref,
                    saldo_contractual_referencia=saldo_ref,
                    estado_suficiencia=estado,
                )
            )
            cantidad_acumulada, _ = totales_por_producto.get(producto_id, (0.0, unidad_id))
            totales_por_producto[producto_id] = (cantidad_acumulada + cantidad_total, unidad_id)

        detalle = [
            RequerimientoAnualDetalleIn(
                producto_id=producto_id,
                cantidad_estimada_anual=round(cantidad, 4),
                unidad_id=unidad_id,
            )
            for producto_id, (cantidad, unidad_id) in totales_por_producto.items()
        ]

        requerimiento = await requerimiento_repo.crear_con_detalle(
            db, RequerimientoAnualCreate(racion_anual_id=racion_anual_id, detalle=detalle)
        )
        await db.flush()

        recargado = await requerimiento_repo.get_con_detalle(db, requerimiento.requerimiento_anual_id)
        assert recargado is not None
        return recargado

    async def obtener_ultimo(self, db: AsyncSession, racion_anual_id: int) -> list[BomConsolidado]:
        racion = await db.get(RacionAnual, racion_anual_id)
        if racion is None:
            raise ValueError("Ración anual no encontrada")

        stmt = (
            select(BomConsolidado)
            .where(BomConsolidado.racion_anual_id == racion_anual_id)
            .order_by(BomConsolidado.almacen_id, BomConsolidado.producto_id)
        )
        return list((await db.execute(stmt)).scalars().all())


servicio_bom_consolidado = ServicioBomConsolidado()
