from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlmacenCreate(BaseModel):
    codigo: str = Field(max_length=20)
    nombre: str = Field(max_length=200)
    sede_id: int
    direccion: str | None = None
    tipo_comedor: str = Field(max_length=60)
    responsable_id: int


class AlmacenUpdate(BaseModel):
    nombre: str | None = None
    direccion: str | None = None
    tipo_comedor: str | None = None
    responsable_id: int | None = None
    estado: str | None = None


class AlmacenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    almacen_id: int
    codigo: str
    nombre: str
    sede_id: int
    direccion: str | None
    tipo_comedor: str
    responsable_id: int
    estado: str
    creado_en: datetime
