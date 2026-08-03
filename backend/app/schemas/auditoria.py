from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditoriaLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    auditoria_id: int
    entidad: str
    entidad_id: int
    accion: str
    usuario_id: int
    detalle_json: dict | None
    creado_en: datetime
