from datetime import date, datetime

from sqlalchemy import BigInteger, Computed, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalogos import Producto
from app.models.compras import GuiaRemision
from app.models.inspeccion import InspeccionDetalle
from app.models.organizacion import Almacen, UbicacionInterna

# SQLite solo alías el rowid (autoincrement) en columnas declaradas exactamente
# INTEGER PRIMARY KEY; con BIGINT se queda NULL y viola NOT NULL en los tests
# (create_all() solo corre contra SQLite, nunca contra MySQL — ver db/base.py).
# En MySQL este tipo sigue siendo BIGINT AUTO_INCREMENT como pide el esquema.
_BigIntPK = BigInteger().with_variant(Integer, "sqlite")


class IngresoAlmacen(Base):
    __tablename__ = "ingreso_almacen"

    ingreso_almacen_id: Mapped[int] = mapped_column(primary_key=True)
    numero_ingreso: Mapped[str] = mapped_column(String(40), unique=True)
    guia_remision_id: Mapped[int] = mapped_column(ForeignKey("guia_remision.guia_remision_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))  # = guia.almacen_destino_id
    almacenero_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    fecha_ingreso: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    guia_remision: Mapped["GuiaRemision"] = relationship(lazy="joined")
    almacen: Mapped["Almacen"] = relationship(lazy="joined")
    detalle: Mapped[list["IngresoAlmacenDetalle"]] = relationship(
        back_populates="ingreso_almacen", cascade="all, delete-orphan"
    )


class IngresoAlmacenDetalle(Base):
    __tablename__ = "ingreso_almacen_detalle"

    ingreso_almacen_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    ingreso_almacen_id: Mapped[int] = mapped_column(ForeignKey("ingreso_almacen.ingreso_almacen_id"))
    inspeccion_detalle_id: Mapped[int] = mapped_column(ForeignKey("inspeccion_detalle.inspeccion_detalle_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad_ingresada: Mapped[float]
    costo_unitario: Mapped[float]
    ubicacion_id: Mapped[int | None] = mapped_column(ForeignKey("ubicacion_interna.ubicacion_id"))

    ingreso_almacen: Mapped["IngresoAlmacen"] = relationship(back_populates="detalle")
    inspeccion_detalle: Mapped["InspeccionDetalle"] = relationship(lazy="joined")
    producto: Mapped["Producto"] = relationship(lazy="joined")
    ubicacion: Mapped["UbicacionInterna | None"] = relationship(lazy="joined")


class StockAlmacenProducto(Base):
    __tablename__ = "stock_almacen_producto"

    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"), primary_key=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"), primary_key=True)
    stock_fisico: Mapped[float] = mapped_column(default=0)
    stock_comprometido: Mapped[float] = mapped_column(default=0)
    # GENERATED ALWAYS en MySQL — ver CLAUDE.md sección 7.3 (requiere refresh()
    # explícito tras cada UPDATE de stock_fisico/stock_comprometido).
    stock_disponible: Mapped[float] = mapped_column(
        Computed("stock_fisico - stock_comprometido", persisted=True)
    )
    valor_promedio_unitario: Mapped[float] = mapped_column(default=0)
    valor_valorizado: Mapped[float] = mapped_column(
        Computed("stock_fisico * valor_promedio_unitario", persisted=True)
    )
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    almacen: Mapped["Almacen"] = relationship(lazy="joined")
    producto: Mapped["Producto"] = relationship(lazy="joined")


class KardexMovimiento(Base):
    """Insert-only (RN-06): nunca se hace UPDATE/DELETE; toda corrección es un
    nuevo movimiento de ajuste. Ver crud/stock.py::registrar_movimiento."""

    __tablename__ = "kardex_movimiento"

    kardex_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    tipo_movimiento: Mapped[str] = mapped_column(String(30))
    # INGRESO, SALIDA, AJUSTE, MERMA, DEVOLUCION_PROVEEDOR, DEVOLUCION_COCINA,
    # TRANSFERENCIA_SALIDA, TRANSFERENCIA_INGRESO, INVENTARIO_AJUSTE
    referencia_tipo: Mapped[str] = mapped_column(String(40))
    referencia_id: Mapped[int] = mapped_column(BigInteger)
    cantidad: Mapped[float]
    costo_unitario: Mapped[float]
    saldo_cantidad_resultante: Mapped[float]
    saldo_valorizado_resultante: Mapped[float]
    registrado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    almacen: Mapped["Almacen"] = relationship(lazy="joined")
    producto: Mapped["Producto"] = relationship(lazy="joined")


class BinCardMovimiento(Base):
    """Insert-only (RN-06), igual que KardexMovimiento pero con dimensión de
    ubicación física interna."""

    __tablename__ = "bin_card_movimiento"

    bin_card_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    ubicacion_id: Mapped[int] = mapped_column(ForeignKey("ubicacion_interna.ubicacion_id"))
    tipo_movimiento: Mapped[str] = mapped_column(String(30))
    referencia_tipo: Mapped[str] = mapped_column(String(40))
    referencia_id: Mapped[int] = mapped_column(BigInteger)
    cantidad: Mapped[float]
    saldo_fisico_resultante: Mapped[float]
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    almacen: Mapped["Almacen"] = relationship(lazy="joined")
    producto: Mapped["Producto"] = relationship(lazy="joined")
    ubicacion: Mapped["UbicacionInterna"] = relationship(lazy="joined")


class AjusteInventario(Base):
    __tablename__ = "ajuste_inventario"

    ajuste_id: Mapped[int] = mapped_column(primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad_ajuste: Mapped[float]  # positivo o negativo
    motivo: Mapped[str] = mapped_column(String(255))
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    producto: Mapped["Producto"] = relationship(lazy="joined")


class Merma(Base):
    __tablename__ = "merma"

    merma_id: Mapped[int] = mapped_column(primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad: Mapped[float]
    motivo: Mapped[str] = mapped_column(String(255))  # VENCIMIENTO, DETERIORO, ROTURA...
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    producto: Mapped["Producto"] = relationship(lazy="joined")


class Devolucion(Base):
    __tablename__ = "devolucion"

    devolucion_id: Mapped[int] = mapped_column(primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    tipo: Mapped[str] = mapped_column(String(30))  # A_PROVEEDOR, DESDE_COCINA
    cantidad: Mapped[float]
    referencia_tipo: Mapped[str | None] = mapped_column(String(40))
    referencia_id: Mapped[int | None] = mapped_column(BigInteger)
    motivo: Mapped[str | None] = mapped_column(String(255))
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    producto: Mapped["Producto"] = relationship(lazy="joined")


class InventarioFisico(Base):
    __tablename__ = "inventario_fisico"

    inventario_fisico_id: Mapped[int] = mapped_column(primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    fecha_conteo: Mapped[date] = mapped_column(Date)
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    estado: Mapped[str] = mapped_column(String(20), default="EN_PROCESO")  # EN_PROCESO, CERRADO

    detalle: Mapped[list["InventarioFisicoDetalle"]] = relationship(
        back_populates="inventario_fisico", cascade="all, delete-orphan"
    )


class InventarioFisicoDetalle(Base):
    __tablename__ = "inventario_fisico_detalle"

    inventario_fisico_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    inventario_fisico_id: Mapped[int] = mapped_column(ForeignKey("inventario_fisico.inventario_fisico_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    stock_sistema: Mapped[float]
    stock_contado: Mapped[float]
    # GENERATED ALWAYS en MySQL — requiere refresh() tras el INSERT.
    diferencia: Mapped[float] = mapped_column(Computed("stock_contado - stock_sistema", persisted=True))
    ajuste_generado_id: Mapped[int | None] = mapped_column(ForeignKey("ajuste_inventario.ajuste_id"))

    inventario_fisico: Mapped["InventarioFisico"] = relationship(back_populates="detalle")
    producto: Mapped["Producto"] = relationship(lazy="joined")


class TransferenciaAlmacen(Base):
    __tablename__ = "transferencia_almacen"

    transferencia_id: Mapped[int] = mapped_column(primary_key=True)
    numero_transferencia: Mapped[str] = mapped_column(String(40), unique=True)
    almacen_origen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    almacen_destino_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    responsable_origen_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    responsable_destino_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    fecha_salida: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_recepcion: Mapped[datetime | None] = mapped_column(DateTime)
    estado: Mapped[str] = mapped_column(String(30), default="EN_TRANSITO")
    # EN_TRANSITO, RECIBIDA_CONFORME, RECIBIDA_CON_DIFERENCIA, ANULADA

    almacen_origen: Mapped["Almacen"] = relationship(foreign_keys=[almacen_origen_id], lazy="joined")
    almacen_destino: Mapped["Almacen"] = relationship(foreign_keys=[almacen_destino_id], lazy="joined")
    detalle: Mapped[list["TransferenciaAlmacenDetalle"]] = relationship(
        back_populates="transferencia", cascade="all, delete-orphan"
    )


class TransferenciaAlmacenDetalle(Base):
    __tablename__ = "transferencia_almacen_detalle"

    transferencia_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    transferencia_id: Mapped[int] = mapped_column(ForeignKey("transferencia_almacen.transferencia_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad_enviada: Mapped[float]
    cantidad_recibida: Mapped[float | None]
    # GENERATED ALWAYS en MySQL — requiere refresh() tras registrar la recepción.
    diferencia: Mapped[float] = mapped_column(
        Computed("COALESCE(cantidad_recibida, 0) - cantidad_enviada", persisted=True)
    )
    observacion_diferencia: Mapped[str | None] = mapped_column(String(255))

    transferencia: Mapped["TransferenciaAlmacen"] = relationship(back_populates="detalle")
    producto: Mapped["Producto"] = relationship(lazy="joined")
