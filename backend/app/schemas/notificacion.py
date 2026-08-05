from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notificacion_id: int
    tipo: str
    referencia_id: int
    mensaje: str
    leida: bool
    creado_en: datetime
