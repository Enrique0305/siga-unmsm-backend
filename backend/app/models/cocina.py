from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalogos import Producto
from app.models.organizacion import Almacen, CentroConsumo
from app.models.planificacion import MenuDia


class SolicitudCocina(Base):
    __tablename__ = "solicitud_cocina"

    solicitud_cocina_id: Mapped[int] = mapped_column(primary_key=True)
    numero_solicitud: Mapped[str] = mapped_column(String(40), unique=True)
    centro_consumo_id: Mapped[int] = mapped_column(ForeignKey("centro_consumo.centro_consumo_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))  # = centro_consumo.almacen_id
    menu_dia_id: Mapped[int] = mapped_column(ForeignKey("menu_dia.menu_dia_id"))
    solicitado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    # PENDIENTE, DESPACHADA, ANULADA — ver crud/solicitud_cocina.py
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    centro_consumo: Mapped["CentroConsumo"] = relationship(lazy="joined")
    almacen: Mapped["Almacen"] = relationship(lazy="joined")
    menu_dia: Mapped["MenuDia"] = relationship(lazy="joined")
    detalle: Mapped[list["SolicitudCocinaDetalle"]] = relationship(
        back_populates="solicitud_cocina", cascade="all, delete-orphan"
    )


class SolicitudCocinaDetalle(Base):
    __tablename__ = "solicitud_cocina_detalle"

    solicitud_cocina_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    solicitud_cocina_id: Mapped[int] = mapped_column(ForeignKey("solicitud_cocina.solicitud_cocina_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    cantidad_solicitada: Mapped[float]
    cantidad_teorica_bom: Mapped[float | None]
    # RN-24: suma de dosificacion_detalle.cantidad_bruta_requerida para ese
    # menú_día + centro_consumo + almacén + alimento vinculado al producto;
    # NULL si el producto no tiene alimento_id o no hay dosificación ese día.

    solicitud_cocina: Mapped["SolicitudCocina"] = relationship(back_populates="detalle")
    producto: Mapped["Producto"] = relationship(lazy="joined")


class NotaSalida(Base):
    __tablename__ = "nota_salida"

    nota_salida_id: Mapped[int] = mapped_column(primary_key=True)
    numero_nota: Mapped[str] = mapped_column(String(40), unique=True)
    solicitud_cocina_id: Mapped[int] = mapped_column(ForeignKey("solicitud_cocina.solicitud_cocina_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))  # = solicitud.almacen_id (RN-17)
    almacenero_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    fecha_salida: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    solicitud_cocina: Mapped["SolicitudCocina"] = relationship(lazy="joined")
    detalle: Mapped[list["NotaSalidaDetalle"]] = relationship(
        back_populates="nota_salida", cascade="all, delete-orphan"
    )


class NotaSalidaDetalle(Base):
    __tablename__ = "nota_salida_detalle"

    nota_salida_detalle_id: Mapped[int] = mapped_column(primary_key=True)
    nota_salida_id: Mapped[int] = mapped_column(ForeignKey("nota_salida.nota_salida_id"))
    solicitud_cocina_detalle_id: Mapped[int] = mapped_column(
        ForeignKey("solicitud_cocina_detalle.solicitud_cocina_detalle_id")
    )
    cantidad_despachada: Mapped[float]
    costo_unitario: Mapped[float]

    nota_salida: Mapped["NotaSalida"] = relationship(back_populates="detalle")
    solicitud_cocina_detalle: Mapped["SolicitudCocinaDetalle"] = relationship(lazy="joined")

    @property
    def variacion_pct(self) -> float | None:
        """Consumo real vs. teórico (BOM). None si la línea no tenía teórico."""
        teorica = self.solicitud_cocina_detalle.cantidad_teorica_bom
        if not teorica:
            return None
        return round((self.cantidad_despachada - teorica) / teorica * 100, 2)
