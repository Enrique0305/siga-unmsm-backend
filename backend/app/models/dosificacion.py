from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BigIntPK
from app.models.catalogos import Alimento, Producto
from app.models.organizacion import Almacen


class DosificacionDetalle(Base):
    __tablename__ = "dosificacion_detalle"

    dosificacion_id: Mapped[int] = mapped_column(primary_key=True)
    menu_dia_id: Mapped[int] = mapped_column(ForeignKey("menu_dia.menu_dia_id"))
    plato_id: Mapped[int] = mapped_column(ForeignKey("plato.plato_id"))
    receta_id: Mapped[int] = mapped_column(ForeignKey("receta.receta_id"))
    centro_consumo_id: Mapped[int] = mapped_column(ForeignKey("centro_consumo.centro_consumo_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    alimento_id: Mapped[int] = mapped_column(ForeignKey("alimento.alimento_id"))
    raciones_programadas: Mapped[int]
    cantidad_bruta_requerida: Mapped[float]
    cantidad_neta_requerida: Mapped[float]
    calculado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    alimento: Mapped["Alimento"] = relationship(lazy="joined")


class BomConsolidado(Base):
    """Explosión de materiales consolidada por periodo y almacén (RN-28).

    Foto de referencia generada al consolidar un requerimiento anual desde
    la dosificación ya calculada — ver crud/bom_consolidado.py. bom_consolidado_id
    es BIGINT en MySQL (ver CLAUDE.md sección 7.4, gotcha de SQLite/BigIntPK).
    """

    __tablename__ = "bom_consolidado"

    bom_consolidado_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    tipo_periodo: Mapped[str] = mapped_column(String(20))  # SEMANA, QUINCENA, MES, ANIO
    periodo_inicio: Mapped[date] = mapped_column(Date)
    periodo_fin: Mapped[date] = mapped_column(Date)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad_requerida_total: Mapped[float]
    stock_disponible_referencia: Mapped[float | None]
    saldo_contractual_referencia: Mapped[float | None]
    estado_suficiencia: Mapped[str | None] = mapped_column(String(20))  # SUFICIENTE, ALERTA_STOCK, ALERTA_CONTRATO
    generado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    almacen: Mapped["Almacen"] = relationship(lazy="joined")
    producto: Mapped["Producto"] = relationship(lazy="joined")
