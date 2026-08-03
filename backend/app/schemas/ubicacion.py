from pydantic import BaseModel, ConfigDict, Field


class UbicacionInternaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ubicacion_id: int
    almacen_id: int
    zona: str
    estante: str | None
    nivel: str | None
    contenedor_camara: str | None
    es_cadena_frio: bool


class UbicacionInternaCreate(BaseModel):
    almacen_id: int
    zona: str = Field(max_length=60)
    estante: str | None = Field(default=None, max_length=60)
    nivel: str | None = Field(default=None, max_length=60)
    contenedor_camara: str | None = Field(default=None, max_length=60)
    es_cadena_frio: bool = False
