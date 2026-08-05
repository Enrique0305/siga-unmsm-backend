from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Notificacion(Base):
    """Generada por el job diario de RN-12 (core/jobs.py::
    procesar_alertas_contratos, Sesión 20) — "Notificación a Logística" sin
    infraestructura de email, consultable vía GET /notificaciones."""

    __tablename__ = "notificacion"

    notificacion_id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40))
    # CONTRATO_VIGENCIA | CONTRATO_SALDO
    referencia_id: Mapped[int] = mapped_column(Integer)
    mensaje: Mapped[str] = mapped_column(String(255))
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
