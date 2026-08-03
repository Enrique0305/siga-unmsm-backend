from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalogos import Alimento


class Receta(Base):
    __tablename__ = "receta"
    __table_args__ = (UniqueConstraint("codigo", "version", name="uq_receta_codigo_version"),)

    receta_id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30))
    nombre: Mapped[str] = mapped_column(String(200))
    categoria_preparacion: Mapped[str] = mapped_column(String(30))  # SOPA, SEGUNDO, ENTRADA, BEBIDA, POSTRE
    descripcion: Mapped[str | None] = mapped_column(Text)
    numero_raciones_base: Mapped[int]
    tamano_porcion_g: Mapped[float]
    rendimiento_pct: Mapped[float]
    merma_estimada_pct: Mapped[float] = mapped_column(default=0)
    procedimiento: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    receta_padre_id: Mapped[int | None] = mapped_column(ForeignKey("receta.receta_id"))
    estado: Mapped[str] = mapped_column(String(20), default="BORRADOR")
    # BORRADOR, EN_REVISION, APROBADO, VIGENTE, DESCONTINUADO
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    aprobado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
    aprobado_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ingredientes: Mapped[list["RecetaIngrediente"]] = relationship(
        back_populates="receta", cascade="all, delete-orphan"
    )
    valor_nutricional: Mapped["RecetaValorNutricional | None"] = relationship(
        back_populates="receta", uselist=False, cascade="all, delete-orphan"
    )


class RecetaIngrediente(Base):
    __tablename__ = "receta_ingrediente"

    receta_ingrediente_id: Mapped[int] = mapped_column(primary_key=True)
    receta_id: Mapped[int] = mapped_column(ForeignKey("receta.receta_id"))
    alimento_id: Mapped[int] = mapped_column(ForeignKey("alimento.alimento_id"))
    cantidad_bruta_g: Mapped[float]
    cantidad_neta_g: Mapped[float]
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidad_medida.unidad_id"))
    factor_conversion: Mapped[float] = mapped_column(Float, default=1)
    merma_pct: Mapped[float] = mapped_column(default=0)

    receta: Mapped["Receta"] = relationship(back_populates="ingredientes")
    alimento: Mapped["Alimento"] = relationship(lazy="joined")


class RecetaValorNutricional(Base):
    __tablename__ = "receta_valor_nutricional"

    receta_id: Mapped[int] = mapped_column(ForeignKey("receta.receta_id"), primary_key=True)

    energia_kcal_total: Mapped[float | None]
    proteinas_g_total: Mapped[float | None]
    grasa_total_g_total: Mapped[float | None]
    carbohidratos_g_total: Mapped[float | None]
    fibra_g_total: Mapped[float | None]
    sodio_mg_total: Mapped[float | None]

    energia_kcal_racion: Mapped[float | None]
    proteinas_g_racion: Mapped[float | None]
    grasa_total_g_racion: Mapped[float | None]
    carbohidratos_g_racion: Mapped[float | None]
    fibra_g_racion: Mapped[float | None]
    sodio_mg_racion: Mapped[float | None]

    recalculado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    receta: Mapped["Receta"] = relationship(back_populates="valor_nutricional")
