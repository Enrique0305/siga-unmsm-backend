from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalogos import Producto
from app.models.receta import Receta


class RacionAnual(Base):
    __tablename__ = "racion_anual"

    racion_anual_id: Mapped[int] = mapped_column(primary_key=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.sede_id"))
    centro_consumo_id: Mapped[int] = mapped_column(ForeignKey("centro_consumo.centro_consumo_id"))
    anio: Mapped[int]
    poblacion_atendida: Mapped[int]
    raciones_dia: Mapped[int]
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")  # BORRADOR, APROBADO
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MenuQuincenal(Base):
    __tablename__ = "menu_quincenal"

    menu_id: Mapped[int] = mapped_column(primary_key=True)
    racion_anual_id: Mapped[int] = mapped_column(ForeignKey("racion_anual.racion_anual_id"))
    quincena_inicio: Mapped[date] = mapped_column(Date)
    quincena_fin: Mapped[date] = mapped_column(Date)
    version: Mapped[int] = mapped_column(default=1)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")
    # BORRADOR, EN_REVISION, APROBADO, VIGENTE, HISTORICO
    aprobado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dias: Mapped[list["MenuDia"]] = relationship(back_populates="menu", cascade="all, delete-orphan")


class MenuDia(Base):
    __tablename__ = "menu_dia"

    menu_dia_id: Mapped[int] = mapped_column(primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menu_quincenal.menu_id"))
    fecha: Mapped[date] = mapped_column(Date)
    tipo_servicio: Mapped[str] = mapped_column(String(30))  # DESAYUNO, ALMUERZO, CENA
    raciones_programadas: Mapped[int]

    menu: Mapped["MenuQuincenal"] = relationship(back_populates="dias")
    platos: Mapped[list["Plato"]] = relationship(back_populates="menu_dia", cascade="all, delete-orphan")


class Plato(Base):
    __tablename__ = "plato"

    plato_id: Mapped[int] = mapped_column(primary_key=True)
    menu_dia_id: Mapped[int] = mapped_column(ForeignKey("menu_dia.menu_dia_id"))
    receta_id: Mapped[int] = mapped_column(ForeignKey("receta.receta_id"))
    raciones_override: Mapped[int | None]

    menu_dia: Mapped["MenuDia"] = relationship(back_populates="platos")
    receta: Mapped["Receta"] = relationship(lazy="joined")


class RequerimientoAnual(Base):
    __tablename__ = "requerimiento_anual"

    requerimiento_anual_id: Mapped[int] = mapped_column(primary_key=True)
    racion_anual_id: Mapped[int] = mapped_column(ForeignKey("racion_anual.racion_anual_id"))
    version: Mapped[int] = mapped_column(default=1)
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")
    # BORRADOR, EN_REVISION, APROBADO, VIGENTE — ver crud/requerimiento.py
    presupuesto_referencial_total: Mapped[float | None]
    aprobado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    detalle: Mapped[list["RequerimientoAnualDetalle"]] = relationship(
        back_populates="requerimiento_anual", cascade="all, delete-orphan"
    )


class RequerimientoAnualDetalle(Base):
    __tablename__ = "requerimiento_anual_detalle"

    requerimiento_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    requerimiento_anual_id: Mapped[int] = mapped_column(ForeignKey("requerimiento_anual.requerimiento_anual_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad_estimada_anual: Mapped[float]
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_medida.unidad_id"))
    presupuesto_referencial: Mapped[float | None]

    requerimiento_anual: Mapped["RequerimientoAnual"] = relationship(back_populates="detalle")
    producto: Mapped["Producto"] = relationship(lazy="joined")
