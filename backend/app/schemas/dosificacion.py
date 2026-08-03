from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DosificacionDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dosificacion_id: int
    menu_dia_id: int
    plato_id: int
    receta_id: int
    centro_consumo_id: int
    almacen_id: int
    alimento_id: int
    alimento_codigo: str
    alimento_nombre: str
    raciones_programadas: int
    cantidad_bruta_requerida: float
    cantidad_neta_requerida: float
    calculado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "DosificacionDetalleOut":
        return cls(
            dosificacion_id=obj.dosificacion_id,
            menu_dia_id=obj.menu_dia_id,
            plato_id=obj.plato_id,
            receta_id=obj.receta_id,
            centro_consumo_id=obj.centro_consumo_id,
            almacen_id=obj.almacen_id,
            alimento_id=obj.alimento_id,
            alimento_codigo=obj.alimento.codigo,
            alimento_nombre=obj.alimento.nombre,
            raciones_programadas=obj.raciones_programadas,
            cantidad_bruta_requerida=obj.cantidad_bruta_requerida,
            cantidad_neta_requerida=obj.cantidad_neta_requerida,
            calculado_en=obj.calculado_en,
        )
