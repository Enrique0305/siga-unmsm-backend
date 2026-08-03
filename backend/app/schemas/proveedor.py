from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    proveedor_id: int
    ruc: str
    razon_social: str
    contacto_nombre: str | None
    contacto_telefono: str | None
    contacto_correo: str | None
    estado: str
    creado_en: datetime


class ProveedorCreate(BaseModel):
    ruc: str = Field(min_length=11, max_length=11)
    razon_social: str = Field(max_length=200)
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_telefono: str | None = Field(default=None, max_length=30)
    contacto_correo: str | None = Field(default=None, max_length=150)


class ProveedorUpdate(BaseModel):
    razon_social: str | None = Field(default=None, max_length=200)
    contacto_nombre: str | None = Field(default=None, max_length=150)
    contacto_telefono: str | None = Field(default=None, max_length=30)
    contacto_correo: str | None = Field(default=None, max_length=150)
    estado: str | None = Field(default=None, description="ACTIVO | INACTIVO")
