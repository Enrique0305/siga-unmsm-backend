from datetime import date

from pydantic import BaseModel


class ValorizacionAlmacenOut(BaseModel):
    almacen_id: int
    almacen_codigo: str
    almacen_nombre: str
    valor_valorizado_total: float


class ComparativoConsumoOut(BaseModel):
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    fecha_inicio: date
    fecha_fin: date
    cantidad_teorica: float
    cantidad_comprada: float
    cantidad_recibida: float
    cantidad_despachada: float


class StockBajoOut(BaseModel):
    almacen_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    stock_fisico: float
    stock_minimo_referencial: float


class ProximoVencerOut(BaseModel):
    almacen_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    lote: str | None
    fecha_vencimiento: date
    cantidad_ingresada: float


class ObservacionSinResolverOut(BaseModel):
    almacen_id: int
    guia_remision_id: int
    numero_guia: str
    producto_codigo: str
    producto_nombre: str
    cantidad_observada: float
    acta_estado: str | None  # None si la línea OBSERVADO nunca tuvo acta


class AlertasAlmacenOut(BaseModel):
    stock_bajo: list[StockBajoOut]
    proximos_vencer: list[ProximoVencerOut]
    observaciones_sin_resolver: list[ObservacionSinResolverOut]
