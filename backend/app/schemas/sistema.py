from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ParametroSistemaIn(BaseModel):
    clave: str = Field(max_length=60)
    valor: str = Field(max_length=255)
    descripcion: str | None = Field(default=None, max_length=255)


class ParametroSistemaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    clave: str
    valor: str
    descripcion: str | None
    actualizado_en: datetime
    actualizado_por_id: int | None
