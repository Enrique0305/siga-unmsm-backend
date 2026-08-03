from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

RESULTADOS_INSPECCION = ("CONFORME", "OBSERVADO")
ESTADOS_ACTA = ("ABIERTA", "SUBSANADA", "RECHAZADA")
RESULTADOS_REINSPECCION = ("CONFORME", "NO_CONFORME")


# --------------------------------------------------------------- inspección
class InspeccionDetalleIn(BaseModel):
    guia_remision_detalle_id: int
    cantidad_conforme: float = Field(ge=0)
    cantidad_observada: float = Field(ge=0)

    @model_validator(mode="after")
    def _suma_positiva(self) -> "InspeccionDetalleIn":
        if self.cantidad_conforme + self.cantidad_observada <= 0:
            raise ValueError("cantidad_conforme + cantidad_observada debe ser mayor a 0")
        return self


class InspeccionDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inspeccion_detalle_id: int
    guia_remision_detalle_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_conforme: float
    cantidad_observada: float
    resultado: str

    @classmethod
    def from_model(cls, obj) -> "InspeccionDetalleOut":
        return cls(
            inspeccion_detalle_id=obj.inspeccion_detalle_id,
            guia_remision_detalle_id=obj.guia_remision_detalle_id,
            producto_codigo=obj.guia_remision_detalle.orden_compra_detalle.producto_contratado.producto.codigo,
            producto_nombre=obj.guia_remision_detalle.orden_compra_detalle.producto_contratado.producto.nombre,
            cantidad_conforme=obj.cantidad_conforme,
            cantidad_observada=obj.cantidad_observada,
            resultado=obj.resultado,
        )


class InspeccionCreate(BaseModel):
    guia_remision_id: int
    detalle: list[InspeccionDetalleIn] = Field(min_length=1)


class InspeccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inspeccion_id: int
    guia_remision_id: int
    inspector_id: int
    fecha_inspeccion: datetime


class InspeccionDetailOut(InspeccionOut):
    detalle: list[InspeccionDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "InspeccionDetailOut":
        base = InspeccionOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[InspeccionDetalleOut.from_model(d) for d in obj.detalle])


# ----------------------------------------------------------- acta observación
class ActaObservacionCreate(BaseModel):
    numero_acta: str = Field(max_length=40)
    motivo: str = Field(max_length=255)
    plazo_subsanacion: date


class ActaObservacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    acta_observacion_id: int
    numero_acta: str
    inspeccion_detalle_id: int
    motivo: str
    cantidad_observada: float
    responsable_id: int
    plazo_subsanacion: date
    estado: str
    creado_en: datetime
    plazo_vencido: bool


# ------------------------------------------------------------------ subsanación
class SubsanacionCreate(BaseModel):
    fecha_presentacion: date
    descripcion: str | None = None


class SubsanacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    subsanacion_id: int
    acta_observacion_id: int
    fecha_presentacion: date
    descripcion: str | None
    resultado_reinspeccion: str | None
    inspector_id: int | None
    creado_en: datetime


class SubsanacionReinspeccionUpdate(BaseModel):
    resultado_reinspeccion: str = Field(description="CONFORME | NO_CONFORME")


class ActaObservacionDetailOut(ActaObservacionOut):
    subsanaciones: list[SubsanacionOut]
