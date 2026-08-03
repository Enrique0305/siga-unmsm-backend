from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.compras import GuiaRemision, GuiaRemisionDetalle


class Inspeccion(Base):
    __tablename__ = "inspeccion"

    inspeccion_id: Mapped[int] = mapped_column(primary_key=True)
    guia_remision_id: Mapped[int] = mapped_column(ForeignKey("guia_remision.guia_remision_id"))
    inspector_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    fecha_inspeccion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    guia_remision: Mapped["GuiaRemision"] = relationship(lazy="joined")
    detalle: Mapped[list["InspeccionDetalle"]] = relationship(
        back_populates="inspeccion", cascade="all, delete-orphan"
    )


class InspeccionDetalle(Base):
    __tablename__ = "inspeccion_detalle"
    __table_args__ = (CheckConstraint("cantidad_conforme + cantidad_observada > 0", name="ck_inspeccion_detalle_suma"),)

    inspeccion_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    inspeccion_id: Mapped[int] = mapped_column(ForeignKey("inspeccion.inspeccion_id"))
    guia_remision_detalle_id: Mapped[int] = mapped_column(ForeignKey("guia_remision_detalle.guia_remision_detalle_id"))
    cantidad_conforme: Mapped[float] = mapped_column(default=0)
    cantidad_observada: Mapped[float] = mapped_column(default=0)
    resultado: Mapped[str] = mapped_column(String(20))
    # CONFORME, OBSERVADO — derivado en el servidor, ver crud/inspeccion.py

    inspeccion: Mapped["Inspeccion"] = relationship(back_populates="detalle")
    guia_remision_detalle: Mapped["GuiaRemisionDetalle"] = relationship(lazy="joined")
    acta_observacion: Mapped["ActaObservacion | None"] = relationship(
        back_populates="inspeccion_detalle", cascade="all, delete-orphan", uselist=False
    )


class ActaObservacion(Base):
    __tablename__ = "acta_observacion"

    acta_observacion_id: Mapped[int] = mapped_column(primary_key=True)
    numero_acta: Mapped[str] = mapped_column(String(40), unique=True)
    inspeccion_detalle_id: Mapped[int] = mapped_column(ForeignKey("inspeccion_detalle.inspeccion_detalle_id"))
    motivo: Mapped[str] = mapped_column(String(255))
    cantidad_observada: Mapped[float]
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    plazo_subsanacion: Mapped[date] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(20), default="ABIERTA")
    # ABIERTA, SUBSANADA, RECHAZADA — ver crud/acta_observacion.py. El cierre
    # de OC con penalidad (RN-11) lo aplica Módulo 5 leyendo este estado.
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    inspeccion_detalle: Mapped["InspeccionDetalle"] = relationship(back_populates="acta_observacion")
    subsanaciones: Mapped[list["Subsanacion"]] = relationship(
        back_populates="acta_observacion", cascade="all, delete-orphan"
    )

    @property
    def plazo_vencido(self) -> bool:
        """RN-11: no hay job/cron en el proyecto — se expone como bandera de
        solo lectura; el cierre automático + penalidad queda para Módulo 5."""
        return self.estado == "ABIERTA" and date.today() > self.plazo_subsanacion


class Subsanacion(Base):
    __tablename__ = "subsanacion"

    subsanacion_id: Mapped[int] = mapped_column(primary_key=True)
    acta_observacion_id: Mapped[int] = mapped_column(ForeignKey("acta_observacion.acta_observacion_id"))
    fecha_presentacion: Mapped[date] = mapped_column(Date)
    descripcion: Mapped[str | None] = mapped_column(Text)
    resultado_reinspeccion: Mapped[str | None] = mapped_column(String(20))
    # CONFORME, NO_CONFORME — nulo hasta que el inspector registra el resultado
    inspector_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    acta_observacion: Mapped["ActaObservacion"] = relationship(back_populates="subsanaciones")
