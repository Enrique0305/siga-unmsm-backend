from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.organizacion import Rol


class Usuario(Base):
    __tablename__ = "usuario"

    usuario_id: Mapped[int] = mapped_column(primary_key=True)
    nombres: Mapped[str] = mapped_column(String(150))
    apellidos: Mapped[str] = mapped_column(String(150))
    correo: Mapped[str] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol_id: Mapped[int] = mapped_column(ForeignKey("rol.rol_id"))
    sede_id: Mapped[int | None] = mapped_column(ForeignKey("sede.sede_id"))
    proveedor_id: Mapped[int | None] = mapped_column(ForeignKey("proveedor.proveedor_id"))
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO")
    creado_en: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rol: Mapped["Rol"] = relationship(lazy="joined")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"
