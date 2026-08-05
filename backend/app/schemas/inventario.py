from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

TIPOS_DEVOLUCION = ("A_PROVEEDOR", "DESDE_COCINA")
ESTADOS_TRANSFERENCIA = ("EN_TRANSITO", "RECIBIDA_CONFORME", "RECIBIDA_CON_DIFERENCIA", "ANULADA")


# ------------------------------------------------------------------- stock
class StockAlmacenProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    almacen_id: int
    almacen_codigo: str
    almacen_nombre: str
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    stock_fisico: float
    stock_comprometido: float
    stock_disponible: float
    valor_promedio_unitario: float
    valor_valorizado: float
    actualizado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "StockAlmacenProductoOut":
        return cls(
            almacen_id=obj.almacen_id,
            almacen_codigo=obj.almacen.codigo,
            almacen_nombre=obj.almacen.nombre,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            stock_fisico=obj.stock_fisico,
            stock_comprometido=obj.stock_comprometido,
            stock_disponible=obj.stock_disponible,
            valor_promedio_unitario=obj.valor_promedio_unitario,
            valor_valorizado=obj.valor_valorizado,
            actualizado_en=obj.actualizado_en,
        )


# ---------------------------------------------- parámetro de stock mínimo
class AlmacenProductoParametroIn(BaseModel):
    almacen_id: int
    producto_id: int
    stock_minimo: float = Field(gt=0)


class AlmacenProductoParametroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    almacen_id: int
    almacen_codigo: str
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    stock_minimo: float

    @classmethod
    def from_model(cls, obj) -> "AlmacenProductoParametroOut":
        return cls(
            almacen_id=obj.almacen_id,
            almacen_codigo=obj.almacen.codigo,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            stock_minimo=obj.stock_minimo,
        )


class KardexMovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kardex_id: int
    almacen_id: int
    almacen_codigo: str
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    tipo_movimiento: str
    referencia_tipo: str
    referencia_id: int
    cantidad: float
    costo_unitario: float
    saldo_cantidad_resultante: float
    saldo_valorizado_resultante: float
    registrado_por_id: int
    creado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "KardexMovimientoOut":
        return cls(
            kardex_id=obj.kardex_id,
            almacen_id=obj.almacen_id,
            almacen_codigo=obj.almacen.codigo,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            tipo_movimiento=obj.tipo_movimiento,
            referencia_tipo=obj.referencia_tipo,
            referencia_id=obj.referencia_id,
            cantidad=obj.cantidad,
            costo_unitario=obj.costo_unitario,
            saldo_cantidad_resultante=obj.saldo_cantidad_resultante,
            saldo_valorizado_resultante=obj.saldo_valorizado_resultante,
            registrado_por_id=obj.registrado_por_id,
            creado_en=obj.creado_en,
        )


class BinCardMovimientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bin_card_id: int
    almacen_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    ubicacion_id: int
    tipo_movimiento: str
    referencia_tipo: str
    referencia_id: int
    cantidad: float
    saldo_fisico_resultante: float
    creado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "BinCardMovimientoOut":
        return cls(
            bin_card_id=obj.bin_card_id,
            almacen_id=obj.almacen_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            ubicacion_id=obj.ubicacion_id,
            tipo_movimiento=obj.tipo_movimiento,
            referencia_tipo=obj.referencia_tipo,
            referencia_id=obj.referencia_id,
            cantidad=obj.cantidad,
            saldo_fisico_resultante=obj.saldo_fisico_resultante,
            creado_en=obj.creado_en,
        )


# ---------------------------------------------------------------- ingreso
class IngresoAlmacenDetalleIn(BaseModel):
    inspeccion_detalle_id: int
    cantidad_ingresada: float = Field(gt=0)
    ubicacion_id: int | None = None


class IngresoAlmacenDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingreso_almacen_detalle_id: int
    inspeccion_detalle_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_ingresada: float
    costo_unitario: float
    ubicacion_id: int | None

    @classmethod
    def from_model(cls, obj) -> "IngresoAlmacenDetalleOut":
        return cls(
            ingreso_almacen_detalle_id=obj.ingreso_almacen_detalle_id,
            inspeccion_detalle_id=obj.inspeccion_detalle_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            cantidad_ingresada=obj.cantidad_ingresada,
            costo_unitario=obj.costo_unitario,
            ubicacion_id=obj.ubicacion_id,
        )


class IngresoAlmacenCreate(BaseModel):
    numero_ingreso: str = Field(max_length=40)
    guia_remision_id: int
    detalle: list[IngresoAlmacenDetalleIn] = Field(min_length=1)


class IngresoAlmacenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingreso_almacen_id: int
    numero_ingreso: str
    guia_remision_id: int
    almacen_id: int
    almacenero_id: int
    fecha_ingreso: datetime


class IngresoAlmacenDetailOut(IngresoAlmacenOut):
    detalle: list[IngresoAlmacenDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "IngresoAlmacenDetailOut":
        base = IngresoAlmacenOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[IngresoAlmacenDetalleOut.from_model(d) for d in obj.detalle])


# -------------------------------------------------- ajuste / merma / devolución
class AjusteInventarioCreate(BaseModel):
    almacen_id: int
    producto_id: int
    cantidad_ajuste: float
    motivo: str = Field(max_length=255)

    @model_validator(mode="after")
    def _no_cero(self) -> "AjusteInventarioCreate":
        if self.cantidad_ajuste == 0:
            raise ValueError("cantidad_ajuste no puede ser 0")
        return self


class AjusteInventarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ajuste_id: int
    almacen_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_ajuste: float
    motivo: str
    responsable_id: int
    creado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "AjusteInventarioOut":
        return cls(
            ajuste_id=obj.ajuste_id,
            almacen_id=obj.almacen_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            cantidad_ajuste=obj.cantidad_ajuste,
            motivo=obj.motivo,
            responsable_id=obj.responsable_id,
            creado_en=obj.creado_en,
        )


class MermaCreate(BaseModel):
    almacen_id: int
    producto_id: int
    cantidad: float = Field(gt=0)
    motivo: str = Field(max_length=255)


class MermaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merma_id: int
    almacen_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad: float
    motivo: str
    responsable_id: int
    creado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "MermaOut":
        return cls(
            merma_id=obj.merma_id,
            almacen_id=obj.almacen_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            cantidad=obj.cantidad,
            motivo=obj.motivo,
            responsable_id=obj.responsable_id,
            creado_en=obj.creado_en,
        )


class DevolucionCreate(BaseModel):
    almacen_id: int
    producto_id: int
    tipo: str = Field(description="A_PROVEEDOR | DESDE_COCINA")
    cantidad: float = Field(gt=0)
    referencia_tipo: str | None = Field(default=None, max_length=40)
    referencia_id: int | None = None
    motivo: str | None = Field(default=None, max_length=255)


class DevolucionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    devolucion_id: int
    almacen_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    tipo: str
    cantidad: float
    referencia_tipo: str | None
    referencia_id: int | None
    motivo: str | None
    responsable_id: int
    creado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "DevolucionOut":
        return cls(
            devolucion_id=obj.devolucion_id,
            almacen_id=obj.almacen_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            tipo=obj.tipo,
            cantidad=obj.cantidad,
            referencia_tipo=obj.referencia_tipo,
            referencia_id=obj.referencia_id,
            motivo=obj.motivo,
            responsable_id=obj.responsable_id,
            creado_en=obj.creado_en,
        )


# --------------------------------------------------------- inventario físico
class InventarioFisicoDetalleIn(BaseModel):
    producto_id: int
    stock_contado: float = Field(ge=0)


class InventarioFisicoDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventario_fisico_detalle_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    stock_sistema: float
    stock_contado: float
    diferencia: float
    ajuste_generado_id: int | None

    @classmethod
    def from_model(cls, obj) -> "InventarioFisicoDetalleOut":
        return cls(
            inventario_fisico_detalle_id=obj.inventario_fisico_detalle_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            stock_sistema=obj.stock_sistema,
            stock_contado=obj.stock_contado,
            diferencia=obj.diferencia,
            ajuste_generado_id=obj.ajuste_generado_id,
        )


class InventarioFisicoCreate(BaseModel):
    almacen_id: int
    fecha_conteo: date
    detalle: list[InventarioFisicoDetalleIn] = Field(min_length=1)


class InventarioFisicoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inventario_fisico_id: int
    almacen_id: int
    fecha_conteo: date
    responsable_id: int
    estado: str


class InventarioFisicoDetailOut(InventarioFisicoOut):
    detalle: list[InventarioFisicoDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "InventarioFisicoDetailOut":
        base = InventarioFisicoOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[InventarioFisicoDetalleOut.from_model(d) for d in obj.detalle])


# ----------------------------------------------------------- transferencia
class TransferenciaAlmacenDetalleIn(BaseModel):
    producto_id: int
    cantidad_enviada: float = Field(gt=0)


class TransferenciaAlmacenDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transferencia_detalle_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_enviada: float
    cantidad_recibida: float | None
    diferencia: float
    observacion_diferencia: str | None

    @classmethod
    def from_model(cls, obj) -> "TransferenciaAlmacenDetalleOut":
        return cls(
            transferencia_detalle_id=obj.transferencia_detalle_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            cantidad_enviada=obj.cantidad_enviada,
            cantidad_recibida=obj.cantidad_recibida,
            diferencia=obj.diferencia,
            observacion_diferencia=obj.observacion_diferencia,
        )


class TransferenciaAlmacenCreate(BaseModel):
    numero_transferencia: str = Field(max_length=40)
    almacen_origen_id: int
    almacen_destino_id: int
    detalle: list[TransferenciaAlmacenDetalleIn] = Field(min_length=1)


class TransferenciaAlmacenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transferencia_id: int
    numero_transferencia: str
    almacen_origen_id: int
    almacen_destino_id: int
    responsable_origen_id: int
    responsable_destino_id: int | None
    fecha_salida: datetime
    fecha_recepcion: datetime | None
    estado: str


class TransferenciaAlmacenDetailOut(TransferenciaAlmacenOut):
    detalle: list[TransferenciaAlmacenDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "TransferenciaAlmacenDetailOut":
        base = TransferenciaAlmacenOut.model_validate(obj)
        return cls(**base.model_dump(), detalle=[TransferenciaAlmacenDetalleOut.from_model(d) for d in obj.detalle])


class TransferenciaRecepcionDetalleIn(BaseModel):
    transferencia_detalle_id: int
    cantidad_recibida: float = Field(ge=0)
    observacion_diferencia: str | None = Field(default=None, max_length=255)


class TransferenciaRecepcionIn(BaseModel):
    detalle: list[TransferenciaRecepcionDetalleIn] = Field(min_length=1)
