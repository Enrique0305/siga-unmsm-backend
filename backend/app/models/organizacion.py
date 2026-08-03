from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Rol(Base):
    __tablename__ = "rol"

    rol_id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True)
    acceso_todos_almacenes: Mapped[bool] = mapped_column(Boolean, default=False)
    descripcion: Mapped[str | None] = mapped_column(String(255))


class Sede(Base):
    __tablename__ = "sede"

    sede_id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    direccion: Mapped[str | None] = mapped_column(String(255))


class Almacen(Base):
    __tablename__ = "almacen"

    almacen_id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    nombre: Mapped[str] = mapped_column(String(200))
    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.sede_id"))
    direccion: Mapped[str | None] = mapped_column(String(255))
    tipo_comedor: Mapped[str] = mapped_column(String(60))
    responsable_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sede: Mapped["Sede"] = relationship()


class UsuarioAlmacenAcceso(Base):
    __tablename__ = "usuario_almacen_acceso"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"), primary_key=True)
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"), primary_key=True)


class CentroConsumo(Base):
    __tablename__ = "centro_consumo"

    centro_consumo_id: Mapped[int] = mapped_column(primary_key=True)
    sede_id: Mapped[int] = mapped_column(ForeignKey("sede.sede_id"))
    almacen_id: Mapped[int] = mapped_column(ForeignKey("almacen.almacen_id"))
    nombre: Mapped[str] = mapped_column(String(150))
    poblacion_referencia: Mapped[int | None]
