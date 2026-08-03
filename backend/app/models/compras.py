from datetime import date, datetime

from sqlalchemy import Computed, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.contratos import Contrato, ProductoContratado, Proveedor
from app.models.organizacion import Almacen
from app.models.planificacion import MenuQuincenal


class OrdenCompra(Base):
    __tablename__ = "orden_compra"

    orden_compra_id: Mapped[int] = mapped_column(primary_key=True)
    numero_oc: Mapped[str] = mapped_column(String(40), unique=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contrato.contrato_id"))
    periodo_mes: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="EMITIDA")
    # EMITIDA, ANULADA — ver crud/orden_compra.py. Los estados terminales
    # (CERRADO, PAGADO, PENALIZADO de RN-10) los fija Inspección/Pagos.
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    contrato: Mapped["Contrato"] = relationship(lazy="joined")
    detalle: Mapped[list["OrdenCompraDetalle"]] = relationship(
        back_populates="orden_compra", cascade="all, delete-orphan"
    )


class OrdenCompraDetalle(Base):
    __tablename__ = "orden_compra_detalle"

    orden_compra_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.orden_compra_id"))
    producto_contratado_id: Mapped[int] = mapped_column(ForeignKey("producto_contratado.producto_contratado_id"))
    cantidad_solicitada: Mapped[float]
    precio_unitario_aplicado: Mapped[float]
    cantidad_ingresada_acumulada: Mapped[float] = mapped_column(default=0)
    # Columna GENERATED ALWAYS en MySQL — nunca la escribe el ORM (ver
    # CLAUDE.md sección 7.3: requiere refresh() explícito tras cada UPDATE
    # de cantidad_ingresada_acumulada).
    saldo_oc: Mapped[float] = mapped_column(
        Computed("cantidad_solicitada - cantidad_ingresada_acumulada", persisted=True)
    )

    orden_compra: Mapped["OrdenCompra"] = relationship(back_populates="detalle")
    producto_contratado: Mapped["ProductoContratado"] = relationship(lazy="joined")
    distribucion: Mapped[list["OrdenCompraDistribucion"]] = relationship(
        back_populates="orden_compra_detalle", cascade="all, delete-orphan"
    )


class OrdenCompraDistribucion(Base):
    """[MULTIALMACÉN] Distribución de cada línea de OC entre 1..N almacenes destino (RN-15)."""

    __tablename__ = "orden_compra_distribucion"
    __table_args__ = (
        UniqueConstraint("orden_compra_detalle_id", "almacen_id", name="uq_ocd_almacen"),
    )

    orden_compra_distribucion_id: Mapped[int] = mapped_column(primary_key=True)
    orden_compra_detalle_id: Mapped[int] = mapped_column(ForeignKey("orden_compra_detalle.orden_compra_detalle_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    cantidad_distribuida: Mapped[float]

    orden_compra_detalle: Mapped["OrdenCompraDetalle"] = relationship(back_populates="distribucion")
    almacen: Mapped["Almacen"] = relationship(lazy="joined")


class PedidoSemanal(Base):
    """[MULTIALMACÉN] Pedido semanal por sede + menú + almacén (RN-16)."""

    __tablename__ = "pedido_semanal"
    __table_args__ = (
        UniqueConstraint("menu_id", "almacen_id", "semana_inicio", name="uq_pedido_semanal_menu_almacen_semana"),
    )

    pedido_semanal_id: Mapped[int] = mapped_column(primary_key=True)
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.orden_compra_id"))
    menu_id: Mapped[int] = mapped_column(ForeignKey("menu_quincenal.menu_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    semana_inicio: Mapped[date] = mapped_column(Date)
    semana_fin: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="PROGRAMADO")

    orden_compra: Mapped["OrdenCompra"] = relationship(lazy="joined")
    menu: Mapped["MenuQuincenal"] = relationship(lazy="joined")
    almacen: Mapped["Almacen"] = relationship(lazy="joined")


class GuiaRemision(Base):
    """[MULTIALMACÉN] Toda guía indica almacén de destino obligatorio (RN-13)."""

    __tablename__ = "guia_remision"
    __table_args__ = (UniqueConstraint("numero_guia", "proveedor_id", name="uq_guia_remision_numero_proveedor"),)

    guia_remision_id: Mapped[int] = mapped_column(primary_key=True)
    numero_guia: Mapped[str] = mapped_column(String(40))
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.proveedor_id"))
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.orden_compra_id"))
    pedido_semanal_id: Mapped[int] = mapped_column(ForeignKey("pedido_semanal.pedido_semanal_id"))
    almacen_destino_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    fecha_entrega: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    # PENDIENTE, y luego PARCIAL/CONFORME/OBSERVADO/SUBSANADO/CERRADO/
    # PENALIZADO — esas transiciones las gobierna el módulo de Inspección.
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    proveedor: Mapped["Proveedor"] = relationship(lazy="joined")
    orden_compra: Mapped["OrdenCompra"] = relationship(lazy="joined")
    pedido_semanal: Mapped["PedidoSemanal"] = relationship(lazy="joined")
    almacen_destino: Mapped["Almacen"] = relationship(lazy="joined")
    detalle: Mapped[list["GuiaRemisionDetalle"]] = relationship(
        back_populates="guia_remision", cascade="all, delete-orphan"
    )


class GuiaRemisionDetalle(Base):
    __tablename__ = "guia_remision_detalle"

    guia_remision_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    guia_remision_id: Mapped[int] = mapped_column(ForeignKey("guia_remision.guia_remision_id"))
    orden_compra_detalle_id: Mapped[int] = mapped_column(ForeignKey("orden_compra_detalle.orden_compra_detalle_id"))
    cantidad_entregada: Mapped[float]
    lote: Mapped[str | None] = mapped_column(String(60))
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date)

    guia_remision: Mapped["GuiaRemision"] = relationship(back_populates="detalle")
    orden_compra_detalle: Mapped["OrdenCompraDetalle"] = relationship(lazy="joined")
