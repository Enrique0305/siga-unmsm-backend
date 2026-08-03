from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.compras import OrdenCompra, OrdenCompraDetalle
from app.models.inspeccion import ActaObservacion


class Penalidad(Base):
    __tablename__ = "penalidad"

    penalidad_id: Mapped[int] = mapped_column(primary_key=True)
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.orden_compra_id"))
    acta_observacion_id: Mapped[int | None] = mapped_column(ForeignKey("acta_observacion.acta_observacion_id"))
    monto_penalidad: Mapped[float]
    motivo: Mapped[str] = mapped_column(String(255))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    orden_compra: Mapped["OrdenCompra"] = relationship(lazy="joined")
    acta_observacion: Mapped["ActaObservacion | None"] = relationship(lazy="joined")


class InformeConformidadPago(Base):
    __tablename__ = "informe_conformidad_pago"

    informe_id: Mapped[int] = mapped_column(primary_key=True)
    numero_informe: Mapped[str] = mapped_column(String(40), unique=True)
    orden_compra_id: Mapped[int] = mapped_column(ForeignKey("orden_compra.orden_compra_id"))
    monto_conforme_total: Mapped[float]
    monto_retenido_total: Mapped[float] = mapped_column(default=0)
    monto_penalidad_total: Mapped[float] = mapped_column(default=0)
    generado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    estado: Mapped[str] = mapped_column(String(20), default="ENVIADO")
    # ENVIADO, RECIBIDO, EN_PROCESO_DE_PAGO, PAGADO, DEVUELTO
    fecha_envio: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_pago: Mapped[datetime | None] = mapped_column(DateTime)

    orden_compra: Mapped["OrdenCompra"] = relationship(lazy="joined")
    detalle: Mapped[list["InformeConformidadDetalle"]] = relationship(
        back_populates="informe", cascade="all, delete-orphan"
    )


class InformeConformidadDetalle(Base):
    __tablename__ = "informe_conformidad_detalle"

    informe_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    informe_id: Mapped[int] = mapped_column(ForeignKey("informe_conformidad_pago.informe_id"))
    orden_compra_detalle_id: Mapped[int] = mapped_column(ForeignKey("orden_compra_detalle.orden_compra_detalle_id"))
    cantidad_conforme: Mapped[float]
    monto_conforme: Mapped[float]
    cantidad_retenida: Mapped[float] = mapped_column(default=0)
    monto_retenido: Mapped[float] = mapped_column(default=0)

    informe: Mapped["InformeConformidadPago"] = relationship(back_populates="detalle")
    orden_compra_detalle: Mapped["OrdenCompraDetalle"] = relationship(lazy="joined")
