from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_RECETA = ("BORRADOR", "EN_REVISION", "APROBADO", "VIGENTE", "DESCONTINUADO")
CATEGORIAS_PREPARACION = ("SOPA", "SEGUNDO", "ENTRADA", "BEBIDA", "POSTRE")


class RecetaIngredienteIn(BaseModel):
    alimento_id: int
    cantidad_bruta_g: float = Field(gt=0)
    cantidad_neta_g: float = Field(gt=0)
    unidad_id: int
    factor_conversion: float = Field(default=1, gt=0)
    merma_pct: float = Field(default=0, ge=0, le=100)


class RecetaIngredienteOut(RecetaIngredienteIn):
    model_config = ConfigDict(from_attributes=True)

    receta_ingrediente_id: int
    alimento_codigo: str
    alimento_nombre: str

    @classmethod
    def from_model(cls, obj) -> "RecetaIngredienteOut":
        return cls(
            receta_ingrediente_id=obj.receta_ingrediente_id,
            alimento_id=obj.alimento_id,
            cantidad_bruta_g=obj.cantidad_bruta_g,
            cantidad_neta_g=obj.cantidad_neta_g,
            unidad_id=obj.unidad_id,
            factor_conversion=obj.factor_conversion,
            merma_pct=obj.merma_pct,
            alimento_codigo=obj.alimento.codigo,
            alimento_nombre=obj.alimento.nombre,
        )


class RecetaValorNutricionalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    energia_kcal_total: float | None
    proteinas_g_total: float | None
    grasa_total_g_total: float | None
    carbohidratos_g_total: float | None
    fibra_g_total: float | None
    sodio_mg_total: float | None
    energia_kcal_racion: float | None
    proteinas_g_racion: float | None
    grasa_total_g_racion: float | None
    carbohidratos_g_racion: float | None
    fibra_g_racion: float | None
    sodio_mg_racion: float | None
    recalculado_en: datetime


class RecetaCreate(BaseModel):
    codigo: str = Field(max_length=30)
    nombre: str = Field(max_length=200)
    categoria_preparacion: str
    descripcion: str | None = None
    numero_raciones_base: int = Field(gt=0)
    tamano_porcion_g: float = Field(gt=0)
    rendimiento_pct: float = Field(gt=0, le=100)  # RN-23
    merma_estimada_pct: float = Field(default=0, ge=0, le=100)
    procedimiento: str | None = None
    ingredientes: list[RecetaIngredienteIn] = Field(min_length=1)  # RN-23


class RecetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    receta_id: int
    codigo: str
    nombre: str
    categoria_preparacion: str
    descripcion: str | None
    numero_raciones_base: int
    tamano_porcion_g: float
    rendimiento_pct: float
    merma_estimada_pct: float
    procedimiento: str | None
    version: int
    receta_padre_id: int | None
    estado: str
    creado_en: datetime


class RecetaDetailOut(RecetaOut):
    ingredientes: list[RecetaIngredienteOut]
    valor_nutricional: RecetaValorNutricionalOut | None


class RecetaEstadoUpdate(BaseModel):
    estado: str = Field(description="EN_REVISION | APROBADO | VIGENTE | DESCONTINUADO")
