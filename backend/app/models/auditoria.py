from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, BigIntPK


class AuditoriaLog(Base):
    """Insert-only, poblada automáticamente por el evento de
    `app/core/audit.py` (nunca se escribe a mano desde los CRUD de cada
    módulo)."""

    __tablename__ = "auditoria_log"

    auditoria_id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    entidad: Mapped[str] = mapped_column(String(80))
    entidad_id: Mapped[int] = mapped_column(BigInteger)
    accion: Mapped[str] = mapped_column(String(40))
    # CREAR, ACTUALIZAR, ELIMINAR — ver core/audit.py
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.usuario_id"))
    detalle_json: Mapped[dict | None] = mapped_column(JSON)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
