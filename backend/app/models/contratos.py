from datetime import date, datetime

from sqlalchemy import JSON, Computed, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalogos import Producto
from app.models.planificacion import RequerimientoAnual


class Proveedor(Base):
    __tablename__ = "proveedor"

    proveedor_id: Mapped[int] = mapped_column(primary_key=True)
    ruc: Mapped[str] = mapped_column(String(11), unique=True)
    razon_social: Mapped[str] = mapped_column(String(200))
    contacto_nombre: Mapped[str | None] = mapped_column(String(150))
    contacto_telefono: Mapped[str | None] = mapped_column(String(30))
    contacto_correo: Mapped[str | None] = mapped_column(String(150))
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Contrato(Base):
    __tablename__ = "contrato"

    contrato_id: Mapped[int] = mapped_column(primary_key=True)
    numero_contrato: Mapped[str] = mapped_column(String(40), unique=True)
    proveedor_id: Mapped[int] = mapped_column(ForeignKey("proveedor.proveedor_id"))
    requerimiento_anual_id: Mapped[int] = mapped_column(ForeignKey("requerimiento_anual.requerimiento_anual_id"))
    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date] = mapped_column(Date)
    presupuesto_total: Mapped[float]
    condiciones: Mapped[str | None] = mapped_column(Text)
    penalidad_json: Mapped[dict | None] = mapped_column(JSON)
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    estado: Mapped[str] = mapped_column(String(20), default="VIGENTE")
    # VIGENTE, SUSPENDIDO, CERRADO — ver crud/contrato.py
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    proveedor: Mapped["Proveedor"] = relationship(lazy="joined")
    requerimiento_anual: Mapped["RequerimientoAnual"] = relationship(lazy="joined")
    cronograma: Mapped[list["CronogramaEntrega"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )
    productos_contratados: Mapped[list["ProductoContratado"]] = relationship(
        back_populates="contrato", cascade="all, delete-orphan"
    )

    @property
    def dias_para_vencer(self) -> int:
        return (self.fecha_fin - date.today()).days

    @property
    def alerta_vigencia(self) -> bool:
        """RN-12: alerta cuando la vigencia está a 30 días o menos de vencer."""
        return 0 <= self.dias_para_vencer <= 30


class CronogramaEntrega(Base):
    __tablename__ = "cronograma_entrega"

    cronograma_id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contrato.contrato_id"))
    periodo: Mapped[str] = mapped_column(String(20))
    fecha_programada: Mapped[date] = mapped_column(Date)

    contrato: Mapped["Contrato"] = relationship(back_populates="cronograma")


class ProductoContratado(Base):
    """Saldo físico/monetario GLOBAL del contrato (no distingue almacén, ver RN-19)."""

    __tablename__ = "producto_contratado"
    __table_args__ = (UniqueConstraint("contrato_id", "producto_id", name="uq_producto_contratado_contrato_producto"),)

    producto_contratado_id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contrato.contrato_id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.producto_id"))
    precio_unitario: Mapped[float]
    cantidad_contratada: Mapped[float]
    # Columna GENERATED ALWAYS AS (precio_unitario * cantidad_contratada) STORED en MySQL:
    # se marca Computed() para que el ORM la lea pero nunca intente escribirla.
    tope_monetario: Mapped[float] = mapped_column(
        Computed("precio_unitario * cantidad_contratada", persisted=True)
    )
    saldo_fisico: Mapped[float]
    saldo_monetario: Mapped[float]

    contrato: Mapped["Contrato"] = relationship(back_populates="productos_contratados")
    producto: Mapped["Producto"] = relationship(lazy="joined")

    @property
    def porcentaje_saldo_fisico(self) -> float:
        return round((self.saldo_fisico / self.cantidad_contratada) * 100, 2) if self.cantidad_contratada else 0.0

    @property
    def porcentaje_saldo_monetario(self) -> float:
        return round((self.saldo_monetario / self.tope_monetario) * 100, 2) if self.tope_monetario else 0.0

    @property
    def alerta_saldo(self) -> bool:
        """RN-12: alerta cuando el saldo físico o monetario cae a 15% o menos del tope."""
        return self.porcentaje_saldo_fisico <= 15 or self.porcentaje_saldo_monetario <= 15
