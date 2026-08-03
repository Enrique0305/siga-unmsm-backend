from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalogos import Alimento


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
