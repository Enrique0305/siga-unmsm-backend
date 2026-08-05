from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalogos import Producto
from app.models.cocina import NotaSalida, NotaSalidaDetalle, SolicitudCocinaDetalle
from app.models.compras import GuiaRemision, GuiaRemisionDetalle, OrdenCompra, OrdenCompraDetalle
from app.models.contratos import Contrato, ProductoContratado
from app.models.dosificacion import DosificacionDetalle
from app.models.inspeccion import ActaObservacion, InspeccionDetalle
from app.models.inventario import (
    AlmacenProductoParametro,
    IngresoAlmacen,
    IngresoAlmacenDetalle,
    StockAlmacenProducto,
)
from app.models.organizacion import Almacen
from app.models.planificacion import MenuDia


async def valorizacion_inventario(
    db: AsyncSession, almacen_id: int | None = None, sede_id: int | None = None
) -> list[dict]:
    stmt = (
        select(
            StockAlmacenProducto.almacen_id,
            Almacen.codigo,
            Almacen.nombre,
            func.sum(StockAlmacenProducto.valor_valorizado).label("valor_total"),
        )
        .join(Almacen, StockAlmacenProducto.almacen_id == Almacen.almacen_id)
        .group_by(StockAlmacenProducto.almacen_id, Almacen.codigo, Almacen.nombre)
        .order_by(Almacen.codigo)
    )
    if almacen_id is not None:
        stmt = stmt.where(StockAlmacenProducto.almacen_id == almacen_id)
    if sede_id is not None:
        stmt = stmt.where(Almacen.sede_id == sede_id)

    filas = (await db.execute(stmt)).all()
    return [
        {
            "almacen_id": f.almacen_id,
            "almacen_codigo": f.codigo,
            "almacen_nombre": f.nombre,
            "valor_valorizado_total": f.valor_total or 0.0,
        }
        for f in filas
    ]


async def comparativo_consumo(
    db: AsyncSession,
    producto_id: int,
    fecha_inicio: date,
    fecha_fin: date,
    proveedor_id: int | None = None,
) -> dict:
    """Cruza Módulo 1A (dosificación/RN-24), Módulo 3 (OC), Almacén (ingreso)
    y Módulo 4 (nota de salida) — cada suma es independiente, si una parte
    no tiene datos da 0 sin afectar a las demás.

    `proveedor_id` solo filtra `cantidad_comprada` (única de las 4 métricas
    con dimensión de proveedor real, vía OrdenCompra.contrato_id ->
    Contrato.proveedor_id): teórico es una cifra de planificación sin
    proveedor; recibido/despachado ya pasaron el punto de compra y trackean
    movimiento de producto, no de proveedor."""
    producto = await db.get(Producto, producto_id)
    if producto is None:
        raise ValueError("El producto indicado no existe")

    cantidad_teorica = 0.0
    if producto.alimento_id is not None:
        stmt_teorica = (
            select(func.sum(DosificacionDetalle.cantidad_bruta_requerida))
            .join(MenuDia, DosificacionDetalle.menu_dia_id == MenuDia.menu_dia_id)
            .where(
                DosificacionDetalle.alimento_id == producto.alimento_id,
                MenuDia.fecha >= fecha_inicio,
                MenuDia.fecha <= fecha_fin,
            )
        )
        cantidad_teorica = (await db.execute(stmt_teorica)).scalar_one() or 0.0

    stmt_comprada = (
        select(func.sum(OrdenCompraDetalle.cantidad_solicitada))
        .join(
            ProductoContratado,
            OrdenCompraDetalle.producto_contratado_id == ProductoContratado.producto_contratado_id,
        )
        .join(OrdenCompra, OrdenCompraDetalle.orden_compra_id == OrdenCompra.orden_compra_id)
        .where(
            ProductoContratado.producto_id == producto_id,
            OrdenCompra.periodo_mes >= fecha_inicio,
            OrdenCompra.periodo_mes <= fecha_fin,
        )
    )
    if proveedor_id is not None:
        stmt_comprada = stmt_comprada.join(Contrato, OrdenCompra.contrato_id == Contrato.contrato_id).where(
            Contrato.proveedor_id == proveedor_id
        )
    cantidad_comprada = (await db.execute(stmt_comprada)).scalar_one() or 0.0

    stmt_recibida = (
        select(func.sum(IngresoAlmacenDetalle.cantidad_ingresada))
        .join(IngresoAlmacen, IngresoAlmacenDetalle.ingreso_almacen_id == IngresoAlmacen.ingreso_almacen_id)
        .where(
            IngresoAlmacenDetalle.producto_id == producto_id,
            func.date(IngresoAlmacen.fecha_ingreso) >= fecha_inicio,
            func.date(IngresoAlmacen.fecha_ingreso) <= fecha_fin,
        )
    )
    cantidad_recibida = (await db.execute(stmt_recibida)).scalar_one() or 0.0

    stmt_despachada = (
        select(func.sum(NotaSalidaDetalle.cantidad_despachada))
        .join(NotaSalida, NotaSalidaDetalle.nota_salida_id == NotaSalida.nota_salida_id)
        .join(
            SolicitudCocinaDetalle,
            NotaSalidaDetalle.solicitud_cocina_detalle_id == SolicitudCocinaDetalle.solicitud_cocina_detalle_id,
        )
        .where(
            SolicitudCocinaDetalle.producto_id == producto_id,
            func.date(NotaSalida.fecha_salida) >= fecha_inicio,
            func.date(NotaSalida.fecha_salida) <= fecha_fin,
        )
    )
    cantidad_despachada = (await db.execute(stmt_despachada)).scalar_one() or 0.0

    return {
        "producto_id": producto_id,
        "producto_codigo": producto.codigo,
        "producto_nombre": producto.nombre,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "cantidad_teorica": cantidad_teorica,
        "cantidad_comprada": cantidad_comprada,
        "cantidad_recibida": cantidad_recibida,
        "cantidad_despachada": cantidad_despachada,
    }


async def _stock_bajo(db: AsyncSession, almacen_id: int | None, producto_id: int | None = None) -> list[dict]:
    """Umbral efectivo (Sesión 17): el override de almacen_producto_parametro
    manda si existe; si no, cae al stock_minimo_referencial global del
    producto. El campo de salida sigue llamándose stock_minimo_referencial
    por compatibilidad con el schema/frontend ya existentes, pero ahora
    refleja ese umbral efectivo, no siempre el global."""
    umbral = func.coalesce(AlmacenProductoParametro.stock_minimo, Producto.stock_minimo_referencial)
    stmt = (
        select(StockAlmacenProducto, Producto, umbral.label("umbral"))
        .join(Producto, StockAlmacenProducto.producto_id == Producto.producto_id)
        .outerjoin(
            AlmacenProductoParametro,
            (AlmacenProductoParametro.almacen_id == StockAlmacenProducto.almacen_id)
            & (AlmacenProductoParametro.producto_id == StockAlmacenProducto.producto_id),
        )
        .where(umbral.is_not(None), StockAlmacenProducto.stock_fisico < umbral)
    )
    if almacen_id is not None:
        stmt = stmt.where(StockAlmacenProducto.almacen_id == almacen_id)
    if producto_id is not None:
        stmt = stmt.where(StockAlmacenProducto.producto_id == producto_id)

    filas = (await db.execute(stmt)).all()
    return [
        {
            "almacen_id": stock.almacen_id,
            "producto_id": stock.producto_id,
            "producto_codigo": producto.codigo,
            "producto_nombre": producto.nombre,
            "stock_fisico": stock.stock_fisico,
            "stock_minimo_referencial": umbral_efectivo,
        }
        for stock, producto, umbral_efectivo in filas
    ]


async def _proximos_vencer(
    db: AsyncSession, almacen_id: int | None, dias_vencimiento: int, producto_id: int | None = None
) -> list[dict]:
    """Limitación conocida: el esquema no trackea stock por lote
    (stock_almacen_producto es solo por almacén+producto), así que se
    informa la cantidad *ingresada* de ese lote, no la que *queda* en stock
    hoy — no hay forma de saberlo sin un FIFO por lote, que no existe."""
    limite = date.today() + timedelta(days=dias_vencimiento)
    stmt = (
        select(GuiaRemisionDetalle, IngresoAlmacenDetalle, IngresoAlmacen, Producto)
        .join(
            InspeccionDetalle,
            InspeccionDetalle.guia_remision_detalle_id == GuiaRemisionDetalle.guia_remision_detalle_id,
        )
        .join(IngresoAlmacenDetalle, IngresoAlmacenDetalle.inspeccion_detalle_id == InspeccionDetalle.inspeccion_detalle_id)
        .join(IngresoAlmacen, IngresoAlmacenDetalle.ingreso_almacen_id == IngresoAlmacen.ingreso_almacen_id)
        .join(Producto, IngresoAlmacenDetalle.producto_id == Producto.producto_id)
        .where(GuiaRemisionDetalle.fecha_vencimiento.is_not(None), GuiaRemisionDetalle.fecha_vencimiento <= limite)
    )
    if almacen_id is not None:
        stmt = stmt.where(IngresoAlmacen.almacen_id == almacen_id)
    if producto_id is not None:
        stmt = stmt.where(Producto.producto_id == producto_id)

    filas = (await db.execute(stmt)).all()
    return [
        {
            "almacen_id": ingreso.almacen_id,
            "producto_id": producto.producto_id,
            "producto_codigo": producto.codigo,
            "producto_nombre": producto.nombre,
            "lote": grd.lote,
            "fecha_vencimiento": grd.fecha_vencimiento,
            "cantidad_ingresada": iad.cantidad_ingresada,
        }
        for grd, iad, ingreso, producto in filas
    ]


async def _observaciones_sin_resolver(
    db: AsyncSession, almacen_id: int | None, producto_id: int | None = None
) -> list[dict]:
    stmt = (
        select(InspeccionDetalle, GuiaRemisionDetalle, GuiaRemision, ActaObservacion, Producto)
        .join(
            GuiaRemisionDetalle,
            InspeccionDetalle.guia_remision_detalle_id == GuiaRemisionDetalle.guia_remision_detalle_id,
        )
        .join(GuiaRemision, GuiaRemisionDetalle.guia_remision_id == GuiaRemision.guia_remision_id)
        .join(OrdenCompraDetalle, GuiaRemisionDetalle.orden_compra_detalle_id == OrdenCompraDetalle.orden_compra_detalle_id)
        .join(
            ProductoContratado,
            OrdenCompraDetalle.producto_contratado_id == ProductoContratado.producto_contratado_id,
        )
        .join(Producto, ProductoContratado.producto_id == Producto.producto_id)
        .outerjoin(ActaObservacion, ActaObservacion.inspeccion_detalle_id == InspeccionDetalle.inspeccion_detalle_id)
        .where(
            InspeccionDetalle.resultado == "OBSERVADO",
            (ActaObservacion.acta_observacion_id.is_(None)) | (ActaObservacion.estado == "ABIERTA"),
        )
    )
    if almacen_id is not None:
        stmt = stmt.where(GuiaRemision.almacen_destino_id == almacen_id)
    if producto_id is not None:
        stmt = stmt.where(Producto.producto_id == producto_id)

    filas = (await db.execute(stmt)).all()
    return [
        {
            "almacen_id": guia.almacen_destino_id,
            "guia_remision_id": guia.guia_remision_id,
            "numero_guia": guia.numero_guia,
            "producto_codigo": producto.codigo,
            "producto_nombre": producto.nombre,
            "cantidad_observada": insp.cantidad_observada,
            "acta_estado": acta.estado if acta is not None else None,
        }
        for insp, grd, guia, acta, producto in filas
    ]


async def alertas_almacen(
    db: AsyncSession,
    almacen_id: int | None = None,
    dias_vencimiento: int = 30,
    producto_id: int | None = None,
) -> dict:
    return {
        "stock_bajo": await _stock_bajo(db, almacen_id, producto_id),
        "proximos_vencer": await _proximos_vencer(db, almacen_id, dias_vencimiento, producto_id),
        "observaciones_sin_resolver": await _observaciones_sin_resolver(db, almacen_id, producto_id),
    }
