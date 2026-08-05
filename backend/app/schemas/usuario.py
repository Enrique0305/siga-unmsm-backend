from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rol_id: int
    nombre: str
    acceso_todos_almacenes: bool


class UsuarioCreate(BaseModel):
    nombres: str = Field(min_length=1, max_length=150)
    apellidos: str = Field(min_length=1, max_length=150)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    rol_id: int
    sede_id: int | None = None
    proveedor_id: int | None = Field(
        default=None,
        description="Solo para usuarios con rol PROVEEDOR — acota qué contratos/OCs/guías puede ver (Sesión 12).",
    )
    almacen_ids: list[int] = Field(
        default_factory=list,
        description="Almacenes autorizados (RN-20). Ignorado si el rol tiene acceso_todos_almacenes.",
    )


class UsuarioUpdate(BaseModel):
    nombres: str | None = None
    apellidos: str | None = None
    rol_id: int | None = None
    sede_id: int | None = None
    proveedor_id: int | None = None
    estado: str | None = None
    almacen_ids: list[int] | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    usuario_id: int
    nombres: str
    apellidos: str
    correo: EmailStr
    estado: str
    creado_en: datetime
    rol: RolOut
    proveedor_id: int | None = None
    almacen_ids: list[int] = Field(default_factory=list)
