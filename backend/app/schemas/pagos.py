from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_INFORME = ("ENVIADO", "RECIBIDO", "EN_PROCESO_DE_PAGO", "PAGADO", "DEVUELTO")


# ------------------------------------------------------------------ penalidad
class PenalidadCreate(BaseModel):
    orden_compra_id: int
    monto_penalidad: float = Field(gt=0)
    motivo: str = Field(max_length=255)


class PenalidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    penalidad_id: int
    orden_compra_id: int
    acta_observacion_id: int | None
    monto_penalidad: float
    motivo: str
    creado_en: datetime


# ------------------------------------------------------ informe de conformidad
class InformeConformidadDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    informe_detalle_id: int
    orden_compra_detalle_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_conforme: float
    monto_conforme: float
    cantidad_retenida: float
    monto_retenido: float

    @classmethod
    def from_model(cls, obj) -> "InformeConformidadDetalleOut":
        producto = obj.orden_compra_detalle.producto_contratado.producto
        return cls(
            informe_detalle_id=obj.informe_detalle_id,
            orden_compra_detalle_id=obj.orden_compra_detalle_id,
            producto_codigo=producto.codigo,
            producto_nombre=producto.nombre,
            cantidad_conforme=obj.cantidad_conforme,
            monto_conforme=obj.monto_conforme,
            cantidad_retenida=obj.cantidad_retenida,
            monto_retenido=obj.monto_retenido,
        )


class InformeConformidadPagoCreate(BaseModel):
    numero_informe: str = Field(max_length=40)
    orden_compra_id: int


class InformeConformidadPagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    informe_id: int
    numero_informe: str
    orden_compra_id: int
    monto_conforme_total: float
    monto_retenido_total: float
    monto_penalidad_total: float
    generado_por_id: int
    estado: str
    fecha_envio: datetime
    fecha_pago: datetime | None


class InformeConformidadPagoDetailOut(InformeConformidadPagoOut):
    detalle: list[InformeConformidadDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "InformeConformidadPagoDetailOut":
        base = InformeConformidadPagoOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[InformeConformidadDetalleOut.from_model(d) for d in obj.detalle])


class InformeEstadoUpdate(BaseModel):
    estado: str = Field(description="RECIBIDO | EN_PROCESO_DE_PAGO | PAGADO | DEVUELTO")
