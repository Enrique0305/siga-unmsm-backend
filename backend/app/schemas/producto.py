from pydantic import BaseModel, ConfigDict, Field


class UnidadMedidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unidad_id: int
    codigo: str
    nombre: str


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    producto_id: int
    codigo: str
    nombre: str
    categoria: str | None
    alimento_id: int | None
    perecible: bool
    dias_vida_util: int | None
    stock_minimo_referencial: float | None
    estado: str
    unidad: UnidadMedidaOut


class ProductoCreate(BaseModel):
    codigo: str = Field(max_length=30)
    nombre: str = Field(max_length=200)
    categoria: str | None = Field(default=None, max_length=80)
    unidad_id: int
    alimento_id: int | None = None
    perecible: bool = False
    dias_vida_util: int | None = Field(default=None, gt=0)
    stock_minimo_referencial: float | None = Field(default=None, ge=0)


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, max_length=200)
    categoria: str | None = Field(default=None, max_length=80)
    unidad_id: int | None = None
    perecible: bool | None = None
    dias_vida_util: int | None = Field(default=None, gt=0)
    stock_minimo_referencial: float | None = Field(default=None, ge=0)
    estado: str | None = Field(default=None, description="ACTIVO | INACTIVO")
