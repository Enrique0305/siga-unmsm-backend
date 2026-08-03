from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_SOLICITUD_COCINA = ("PENDIENTE", "DESPACHADA", "ANULADA")


# ------------------------------------------------------------- solicitud
class SolicitudCocinaDetalleIn(BaseModel):
    producto_id: int
    cantidad_solicitada: float = Field(gt=0)


class SolicitudCocinaDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    solicitud_cocina_detalle_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_solicitada: float
    cantidad_teorica_bom: float | None

    @classmethod
    def from_model(cls, obj) -> "SolicitudCocinaDetalleOut":
        return cls(
            solicitud_cocina_detalle_id=obj.solicitud_cocina_detalle_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            cantidad_solicitada=obj.cantidad_solicitada,
            cantidad_teorica_bom=obj.cantidad_teorica_bom,
        )


class SolicitudCocinaCreate(BaseModel):
    numero_solicitud: str = Field(max_length=40)
    centro_consumo_id: int
    menu_dia_id: int
    detalle: list[SolicitudCocinaDetalleIn] = Field(min_length=1)


class SolicitudCocinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    solicitud_cocina_id: int
    numero_solicitud: str
    centro_consumo_id: int
    almacen_id: int
    menu_dia_id: int
    solicitado_por_id: int
    estado: str
    creado_en: datetime


class SolicitudCocinaDetailOut(SolicitudCocinaOut):
    detalle: list[SolicitudCocinaDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "SolicitudCocinaDetailOut":
        base = SolicitudCocinaOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[SolicitudCocinaDetalleOut.from_model(d) for d in obj.detalle])


class SolicitudCocinaEstadoUpdate(BaseModel):
    estado: str = Field(description="ANULADA")


# --------------------------------------------------------------- nota salida
class NotaSalidaDetalleIn(BaseModel):
    solicitud_cocina_detalle_id: int
    cantidad_despachada: float = Field(gt=0)


class NotaSalidaDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nota_salida_detalle_id: int
    solicitud_cocina_detalle_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_despachada: float
    costo_unitario: float
    cantidad_teorica_bom: float | None
    variacion_pct: float | None

    @classmethod
    def from_model(cls, obj) -> "NotaSalidaDetalleOut":
        return cls(
            nota_salida_detalle_id=obj.nota_salida_detalle_id,
            solicitud_cocina_detalle_id=obj.solicitud_cocina_detalle_id,
            producto_id=obj.solicitud_cocina_detalle.producto_id,
            producto_codigo=obj.solicitud_cocina_detalle.producto.codigo,
            producto_nombre=obj.solicitud_cocina_detalle.producto.nombre,
            cantidad_despachada=obj.cantidad_despachada,
            costo_unitario=obj.costo_unitario,
            cantidad_teorica_bom=obj.solicitud_cocina_detalle.cantidad_teorica_bom,
            variacion_pct=obj.variacion_pct,
        )


class NotaSalidaCreate(BaseModel):
    numero_nota: str = Field(max_length=40)
    solicitud_cocina_id: int
    detalle: list[NotaSalidaDetalleIn] = Field(min_length=1)


class NotaSalidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    nota_salida_id: int
    numero_nota: str
    solicitud_cocina_id: int
    almacen_id: int
    almacenero_id: int
    fecha_salida: datetime


class NotaSalidaDetailOut(NotaSalidaOut):
    detalle: list[NotaSalidaDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "NotaSalidaDetailOut":
        base = NotaSalidaOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[NotaSalidaDetalleOut.from_model(d) for d in obj.detalle])
