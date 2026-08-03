from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_ORDEN_COMPRA = ("EMITIDA", "ANULADA")


# ------------------------------------------------------------- distribución
class OrdenCompraDistribucionIn(BaseModel):
    almacen_id: int
    cantidad_distribuida: float = Field(gt=0)


class OrdenCompraDistribucionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orden_compra_distribucion_id: int
    almacen_id: int
    almacen_codigo: str
    almacen_nombre: str
    cantidad_distribuida: float

    @classmethod
    def from_model(cls, obj) -> "OrdenCompraDistribucionOut":
        return cls(
            orden_compra_distribucion_id=obj.orden_compra_distribucion_id,
            almacen_id=obj.almacen_id,
            almacen_codigo=obj.almacen.codigo,
            almacen_nombre=obj.almacen.nombre,
            cantidad_distribuida=obj.cantidad_distribuida,
        )


# ----------------------------------------------------- autorización excedente
class AutorizacionExcedenteIn(BaseModel):
    cantidad_excedente: float = Field(gt=0)
    justificacion: str = Field(min_length=1)


class AutorizacionExcedenteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    autorizacion_excedente_id: int
    orden_compra_detalle_id: int
    cantidad_excedente: float
    justificacion: str
    autorizado_por_id: int
    creado_en: datetime


# ------------------------------------------------------------------ detalle
class OrdenCompraDetalleIn(BaseModel):
    producto_contratado_id: int
    cantidad_solicitada: float = Field(gt=0)
    distribucion: list[OrdenCompraDistribucionIn] = Field(min_length=1)


class OrdenCompraDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orden_compra_detalle_id: int
    producto_contratado_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_solicitada: float
    precio_unitario_aplicado: float
    cantidad_ingresada_acumulada: float
    saldo_oc: float
    total_excedente_autorizado: float
    distribucion: list[OrdenCompraDistribucionOut]
    autorizaciones_excedente: list[AutorizacionExcedenteOut]

    @classmethod
    def from_model(cls, obj) -> "OrdenCompraDetalleOut":
        return cls(
            orden_compra_detalle_id=obj.orden_compra_detalle_id,
            producto_contratado_id=obj.producto_contratado_id,
            producto_codigo=obj.producto_contratado.producto.codigo,
            producto_nombre=obj.producto_contratado.producto.nombre,
            cantidad_solicitada=obj.cantidad_solicitada,
            precio_unitario_aplicado=obj.precio_unitario_aplicado,
            cantidad_ingresada_acumulada=obj.cantidad_ingresada_acumulada,
            saldo_oc=obj.saldo_oc,
            total_excedente_autorizado=obj.total_excedente_autorizado,
            distribucion=[OrdenCompraDistribucionOut.from_model(d) for d in obj.distribucion],
            autorizaciones_excedente=[
                AutorizacionExcedenteOut.model_validate(a) for a in obj.autorizaciones_excedente
            ],
        )


# ------------------------------------------------------------- orden compra
class OrdenCompraCreate(BaseModel):
    numero_oc: str = Field(max_length=40)
    contrato_id: int
    periodo_mes: date
    detalle: list[OrdenCompraDetalleIn] = Field(min_length=1)


class OrdenCompraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    orden_compra_id: int
    numero_oc: str
    contrato_id: int
    periodo_mes: date
    estado: str
    responsable_id: int
    creado_en: datetime


class OrdenCompraDetailOut(OrdenCompraOut):
    numero_contrato: str
    detalle: list[OrdenCompraDetalleOut]

    @classmethod
    def from_model(cls, obj) -> "OrdenCompraDetailOut":
        base = OrdenCompraOut.model_validate(obj)
        return cls(
            **base.model_dump(),
            numero_contrato=obj.contrato.numero_contrato,
            detalle=[OrdenCompraDetalleOut.from_model(d) for d in obj.detalle],
        )


class OrdenCompraEstadoUpdate(BaseModel):
    estado: str = Field(description="ANULADA | CERRADO")


# -------------------------------------------------------------- pedido semanal
class PedidoSemanalCreate(BaseModel):
    orden_compra_id: int
    menu_id: int
    almacen_id: int
    semana_inicio: date
    semana_fin: date


class PedidoSemanalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pedido_semanal_id: int
    orden_compra_id: int
    menu_id: int
    almacen_id: int
    almacen_codigo: str
    almacen_nombre: str
    semana_inicio: date
    semana_fin: date
    estado: str

    @classmethod
    def from_model(cls, obj) -> "PedidoSemanalOut":
        return cls(
            pedido_semanal_id=obj.pedido_semanal_id,
            orden_compra_id=obj.orden_compra_id,
            menu_id=obj.menu_id,
            almacen_id=obj.almacen_id,
            almacen_codigo=obj.almacen.codigo,
            almacen_nombre=obj.almacen.nombre,
            semana_inicio=obj.semana_inicio,
            semana_fin=obj.semana_fin,
            estado=obj.estado,
        )


# -------------------------------------------------------------- guía remisión
class GuiaRemisionDetalleIn(BaseModel):
    orden_compra_detalle_id: int
    cantidad_entregada: float = Field(gt=0)
    lote: str | None = Field(default=None, max_length=60)
    fecha_vencimiento: date | None = None


class GuiaRemisionDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guia_remision_detalle_id: int
    orden_compra_detalle_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_entregada: float
    lote: str | None
    fecha_vencimiento: date | None

    @classmethod
    def from_model(cls, obj) -> "GuiaRemisionDetalleOut":
        return cls(
            guia_remision_detalle_id=obj.guia_remision_detalle_id,
            orden_compra_detalle_id=obj.orden_compra_detalle_id,
            producto_codigo=obj.orden_compra_detalle.producto_contratado.producto.codigo,
            producto_nombre=obj.orden_compra_detalle.producto_contratado.producto.nombre,
            cantidad_entregada=obj.cantidad_entregada,
            lote=obj.lote,
            fecha_vencimiento=obj.fecha_vencimiento,
        )


class GuiaRemisionCreate(BaseModel):
    numero_guia: str = Field(max_length=40)
    proveedor_id: int
    orden_compra_id: int
    pedido_semanal_id: int
    almacen_destino_id: int
    fecha_entrega: date
    detalle: list[GuiaRemisionDetalleIn] = Field(min_length=1)


class GuiaRemisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    guia_remision_id: int
    numero_guia: str
    proveedor_id: int
    orden_compra_id: int
    pedido_semanal_id: int
    almacen_destino_id: int
    fecha_entrega: date
    estado: str
    creado_en: datetime


class GuiaRemisionListOut(GuiaRemisionOut):
    proveedor_razon_social: str
    almacen_destino_codigo: str
    almacen_destino_nombre: str

    @classmethod
    def from_model(cls, obj) -> "GuiaRemisionListOut":
        base = GuiaRemisionOut.model_validate(obj)
        return cls(
            **base.model_dump(),
            proveedor_razon_social=obj.proveedor.razon_social,
            almacen_destino_codigo=obj.almacen_destino.codigo,
            almacen_destino_nombre=obj.almacen_destino.nombre,
        )


class GuiaRemisionDetailOut(GuiaRemisionListOut):
    detalle: list[GuiaRemisionDetalleOut]
