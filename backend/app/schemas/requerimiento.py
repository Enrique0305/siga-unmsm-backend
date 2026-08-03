from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_REQUERIMIENTO = ("BORRADOR", "EN_REVISION", "APROBADO", "VIGENTE")


class RequerimientoAnualDetalleIn(BaseModel):
    producto_id: int
    cantidad_estimada_anual: float = Field(gt=0)
    unidad_id: int
    presupuesto_referencial: float | None = Field(default=None, ge=0)


class RequerimientoAnualDetalleOut(RequerimientoAnualDetalleIn):
    model_config = ConfigDict(from_attributes=True)

    requerimiento_detalle_id: int
    producto_codigo: str
    producto_nombre: str

    @classmethod
    def from_model(cls, obj) -> "RequerimientoAnualDetalleOut":
        return cls(
            requerimiento_detalle_id=obj.requerimiento_detalle_id,
            producto_id=obj.producto_id,
            cantidad_estimada_anual=obj.cantidad_estimada_anual,
            unidad_id=obj.unidad_id,
            presupuesto_referencial=obj.presupuesto_referencial,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
        )


class RequerimientoAnualCreate(BaseModel):
    racion_anual_id: int
    presupuesto_referencial_total: float | None = Field(default=None, ge=0)
    detalle: list[RequerimientoAnualDetalleIn] = Field(min_length=1)


class RequerimientoAnualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    requerimiento_anual_id: int
    racion_anual_id: int
    version: int
    estado: str
    presupuesto_referencial_total: float | None
    aprobado_por_id: int | None
    aprobado_en: datetime | None
    creado_en: datetime


class RequerimientoAnualDetailOut(RequerimientoAnualOut):
    detalle: list[RequerimientoAnualDetalleOut]


class RequerimientoAnualEstadoUpdate(BaseModel):
    estado: str = Field(description="EN_REVISION | APROBADO | VIGENTE")
