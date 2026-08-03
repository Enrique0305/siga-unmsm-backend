from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UnidadMedida(Base):
    __tablename__ = "unidad_medida"

    unidad_id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True)
    nombre: Mapped[str] = mapped_column(String(60))


class CategoriaAlimento(Base):
    __tablename__ = "categoria_alimento"

    categoria_alimento_id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)


class Alimento(Base):
    __tablename__ = "alimento"

    alimento_id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    categoria_alimento_id: Mapped[int] = mapped_column(ForeignKey("categoria_alimento.categoria_alimento_id"))
    tipo: Mapped[str] = mapped_column(String(30))  # BASE_TABLA, PREPARADO_IMPORTADO, PREPARACION_INSTITUCIONAL
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")
    creado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    categoria: Mapped["CategoriaAlimento"] = relationship(lazy="joined")
    versiones: Mapped[list["AlimentoVersion"]] = relationship(
        back_populates="alimento", order_by="AlimentoVersion.version.desc()"
    )

    @property
    def version_vigente(self) -> "AlimentoVersion | None":
        return next((v for v in self.versiones if v.vigente), None)


class AlimentoVersion(Base):
    __tablename__ = "alimento_version"

    alimento_version_id: Mapped[int] = mapped_column(primary_key=True)
    alimento_id: Mapped[int] = mapped_column(ForeignKey("alimento.alimento_id"))
    version: Mapped[int]
    fuente: Mapped[str] = mapped_column(String(255))
    fecha_importacion: Mapped[date] = mapped_column(Date)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)

    # valores nutricionales por 100 g
    energia_kcal: Mapped[float | None]
    energia_kj: Mapped[float | None]
    agua_g: Mapped[float | None]
    proteinas_g: Mapped[float | None]
    grasa_total_g: Mapped[float | None]
    carbohidratos_totales_g: Mapped[float | None]
    carbohidratos_disponibles_g: Mapped[float | None]
    fibra_dietaria_g: Mapped[float | None]
    cenizas_g: Mapped[float | None]
    calcio_mg: Mapped[float | None]
    fosforo_mg: Mapped[float | None]
    zinc_mg: Mapped[float | None]
    hierro_mg: Mapped[float | None]
    vitamina_a_ug: Mapped[float | None]
    tiamina_mg: Mapped[float | None]
    riboflavina_mg: Mapped[float | None]
    niacina_mg: Mapped[float | None]
    vitamina_c_mg: Mapped[float | None]
    acido_folico_ug: Mapped[float | None]
    sodio_mg: Mapped[float | None]
    potasio_mg: Mapped[float | None]

    editado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # vigente_key es una columna GENERATED en MySQL (ver 02_modelo_base_datos_v4_mysql.sql);
    # no se mapea aquí porque el ORM nunca debe escribirla, solo la base de datos la calcula.

    alimento: Mapped["Alimento"] = relationship(back_populates="versiones")


class Producto(Base):
    """Catálogo logístico (compras/almacén) — distinto de Alimento (catálogo nutricional)."""

    __tablename__ = "producto"

    producto_id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    categoria: Mapped[str | None] = mapped_column(String(80))
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_medida.unidad_id"))
    alimento_id: Mapped[int | None] = mapped_column(ForeignKey("alimento.alimento_id"))
    perecible: Mapped[bool] = mapped_column(Boolean, default=False)
    dias_vida_util: Mapped[int | None]
    stock_minimo_referencial: Mapped[float | None]
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")

    unidad: Mapped["UnidadMedida"] = relationship(lazy="joined")
