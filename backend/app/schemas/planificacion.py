from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RacionAnualCreate(BaseModel):
    sede_id: int
    centro_consumo_id: int
    anio: int = Field(ge=2020, le=2100)
    poblacion_atendida: int = Field(gt=0)
    raciones_dia: int = Field(gt=0)


class RacionAnualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    racion_anual_id: int
    sede_id: int
    centro_consumo_id: int
    anio: int
    poblacion_atendida: int
    raciones_dia: int
    estado: str
    creado_en: datetime


class RacionAnualEstadoUpdate(BaseModel):
    estado: str = Field(description="APROBADO")


class MenuQuincenalCreate(BaseModel):
    racion_anual_id: int
    quincena_inicio: date
    quincena_fin: date


class MenuQuincenalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_id: int
    racion_anual_id: int
    quincena_inicio: date
    quincena_fin: date
    version: int
    estado: str
    aprobado_por_id: int | None
    aprobado_en: datetime | None
    creado_en: datetime


class MenuQuincenalEstadoUpdate(BaseModel):
    estado: str = Field(description="EN_REVISION | APROBADO | VIGENTE | HISTORICO | BORRADOR")


class MenuDiaCreate(BaseModel):
    fecha: date
    tipo_servicio: str = Field(description="DESAYUNO | ALMUERZO | CENA")
    raciones_programadas: int = Field(gt=0)


class MenuDiaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    menu_dia_id: int
    menu_id: int
    fecha: date
    tipo_servicio: str
    raciones_programadas: int


class PlatoCreate(BaseModel):
    receta_id: int
    raciones_override: int | None = Field(default=None, gt=0)


class PlatoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plato_id: int
    menu_dia_id: int
    receta_id: int
    receta_nombre: str
    raciones_override: int | None

    @classmethod
    def from_model(cls, obj) -> "PlatoOut":
        return cls(
            plato_id=obj.plato_id,
            menu_dia_id=obj.menu_dia_id,
            receta_id=obj.receta_id,
            receta_nombre=obj.receta.nombre,
            raciones_override=obj.raciones_override,
        )


class AporteNutricionalOut(BaseModel):
    """Suma del valor nutricional POR RACIÓN (`RecetaValorNutricional.*_racion`)
    de todos los platos de un día de menú — ej. Desayuno = pan + ponche,
    cada uno ya expresado por porción, no por el tamaño del lote. Recetas
    sin `valor_nutricional` calculado todavía (nunca se corrió
    `recalcular-nutricion`) aportan 0, no rompen la suma."""

    energia_kcal: float
    proteinas_g: float
    grasa_total_g: float
    carbohidratos_g: float
    fibra_g: float
    sodio_mg: float

    @classmethod
    def from_platos(cls, platos: list) -> "AporteNutricionalOut":
        totales = {
            "energia_kcal": 0.0,
            "proteinas_g": 0.0,
            "grasa_total_g": 0.0,
            "carbohidratos_g": 0.0,
            "fibra_g": 0.0,
            "sodio_mg": 0.0,
        }
        for plato in platos:
            valor = plato.receta.valor_nutricional
            if valor is None:
                continue
            totales["energia_kcal"] += valor.energia_kcal_racion or 0
            totales["proteinas_g"] += valor.proteinas_g_racion or 0
            totales["grasa_total_g"] += valor.grasa_total_g_racion or 0
            totales["carbohidratos_g"] += valor.carbohidratos_g_racion or 0
            totales["fibra_g"] += valor.fibra_g_racion or 0
            totales["sodio_mg"] += valor.sodio_mg_racion or 0
        return cls(**{k: round(v, 2) for k, v in totales.items()})


class MenuDiaDetailOut(MenuDiaOut):
    platos: list[PlatoOut]
    aporte_nutricional: AporteNutricionalOut

    @classmethod
    def from_model(cls, obj) -> "MenuDiaDetailOut":
        return cls(
            menu_dia_id=obj.menu_dia_id,
            menu_id=obj.menu_id,
            fecha=obj.fecha,
            tipo_servicio=obj.tipo_servicio,
            raciones_programadas=obj.raciones_programadas,
            platos=[PlatoOut.from_model(p) for p in obj.platos],
            aporte_nutricional=AporteNutricionalOut.from_platos(obj.platos),
        )


class MenuQuincenalDetailOut(MenuQuincenalOut):
    dias: list[MenuDiaOut]
