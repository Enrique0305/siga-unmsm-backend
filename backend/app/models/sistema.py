from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParametroSistema(Base):
    """Almacén clave-valor genérico (Sesión 18, "09 Administración" del
    diseño) — solo ADMIN lo administra (ver api/v1/parametros_sistema.py).
    `valor` se guarda siempre como texto; cada consumidor castea al tipo
    que necesite (ver crud/parametro_sistema.py::obtener_entero)."""

    __tablename__ = "parametro_sistema"

    clave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    actualizado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.usuario_id"))
