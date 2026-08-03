from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ValorNutricional(BaseModel):
    """Los 21 valores por 100 g exigidos por la especificación funcional."""

    model_config = ConfigDict(from_attributes=True)

    energia_kcal: float | None = None
    energia_kj: float | None = None
    agua_g: float | None = None
    proteinas_g: float | None = None
    grasa_total_g: float | None = None
    carbohidratos_totales_g: float | None = None
    carbohidratos_disponibles_g: float | None = None
    fibra_dietaria_g: float | None = None
    cenizas_g: float | None = None
    calcio_mg: float | None = None
    fosforo_mg: float | None = None
    zinc_mg: float | None = None
    hierro_mg: float | None = None
    vitamina_a_ug: float | None = None
    tiamina_mg: float | None = None
    riboflavina_mg: float | None = None
    niacina_mg: float | None = None
    vitamina_c_mg: float | None = None
    acido_folico_ug: float | None = None
    sodio_mg: float | None = None
    potasio_mg: float | None = None


class AlimentoVersionOut(ValorNutricional):
    alimento_version_id: int
    version: int
    fuente: str
    fecha_importacion: date
    vigente: bool
    creado_en: datetime


class AlimentoVersionCreate(ValorNutricional):
    """
    Body para 'corregir valores' (crea una nueva versión, nunca sobre-escribe
    la anterior — ver RN-25/RN-26 del diseño). El servicio se encarga de:
      1) UPDATE alimento_version SET vigente=FALSE WHERE alimento_id=:id AND vigente=TRUE
      2) INSERT de la nueva versión con vigente=TRUE
    """

    fuente: str = Field(max_length=255)


class CategoriaAlimentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    categoria_alimento_id: int
    nombre: str


class AlimentoListOut(BaseModel):
    """Fila de listado — trae solo la versión vigente para no sobrecargar la tabla."""

    model_config = ConfigDict(from_attributes=True)

    alimento_id: int
    codigo: str
    nombre: str
    tipo: str
    estado: str
    categoria: CategoriaAlimentoOut
    version_vigente: AlimentoVersionOut | None


class AlimentoDetailOut(AlimentoListOut):
    """Ficha de detalle — incluye historial completo de versiones."""

    versiones: list[AlimentoVersionOut]


class AlimentoCreate(BaseModel):
    codigo: str = Field(max_length=30)
    nombre: str = Field(max_length=200)
    categoria_alimento_id: int
    tipo: str = Field(
        default="PREPARACION_INSTITUCIONAL",
        description="BASE_TABLA | PREPARADO_IMPORTADO | PREPARACION_INSTITUCIONAL",
    )
    valores: ValorNutricional
    fuente: str = Field(default="Registro institucional", max_length=255)
