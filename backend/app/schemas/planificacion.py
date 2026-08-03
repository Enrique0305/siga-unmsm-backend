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
    creado_en: datetime


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


class MenuDiaDetailOut(MenuDiaOut):
    platos: list[PlatoOut]
