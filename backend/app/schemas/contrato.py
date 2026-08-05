from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

ESTADOS_CONTRATO = ("VIGENTE", "SUSPENDIDO", "CERRADO")


class CronogramaEntregaIn(BaseModel):
    periodo: str = Field(max_length=20)
    fecha_programada: date


class CronogramaEntregaOut(CronogramaEntregaIn):
    model_config = ConfigDict(from_attributes=True)

    cronograma_id: int


class ProductoContratadoIn(BaseModel):
    producto_id: int
    precio_unitario: float = Field(gt=0)
    cantidad_contratada: float = Field(gt=0)


class ProductoContratadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    producto_contratado_id: int
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    precio_unitario: float
    cantidad_contratada: float
    tope_monetario: float
    saldo_fisico: float
    saldo_monetario: float
    porcentaje_saldo_fisico: float
    porcentaje_saldo_monetario: float
    alerta_saldo: bool

    @classmethod
    def from_model(cls, obj, umbral_alerta_saldo: int) -> "ProductoContratadoOut":
        return cls(
            producto_contratado_id=obj.producto_contratado_id,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            precio_unitario=obj.precio_unitario,
            cantidad_contratada=obj.cantidad_contratada,
            tope_monetario=obj.tope_monetario,
            saldo_fisico=obj.saldo_fisico,
            saldo_monetario=obj.saldo_monetario,
            porcentaje_saldo_fisico=obj.porcentaje_saldo_fisico,
            porcentaje_saldo_monetario=obj.porcentaje_saldo_monetario,
            alerta_saldo=obj.calcular_alerta_saldo(umbral_alerta_saldo),
        )


class ContratoCreate(BaseModel):
    numero_contrato: str = Field(max_length=40)
    proveedor_id: int
    requerimiento_anual_id: int
    fecha_inicio: date
    fecha_fin: date
    presupuesto_total: float = Field(gt=0)
    condiciones: str | None = None
    penalidad_json: dict | None = None
    cronograma: list[CronogramaEntregaIn] = Field(default_factory=list)


class ContratoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    contrato_id: int
    numero_contrato: str
    proveedor_id: int
    requerimiento_anual_id: int
    fecha_inicio: date
    fecha_fin: date
    presupuesto_total: float
    condiciones: str | None
    penalidad_json: dict | None
    responsable_id: int
    estado: str
    creado_en: datetime
    dias_para_vencer: int
    alerta_vigencia: bool

    @classmethod
    def from_model(cls, obj, umbral_alerta_vigencia: int) -> "ContratoOut":
        return cls(
            contrato_id=obj.contrato_id,
            numero_contrato=obj.numero_contrato,
            proveedor_id=obj.proveedor_id,
            requerimiento_anual_id=obj.requerimiento_anual_id,
            fecha_inicio=obj.fecha_inicio,
            fecha_fin=obj.fecha_fin,
            presupuesto_total=obj.presupuesto_total,
            condiciones=obj.condiciones,
            penalidad_json=obj.penalidad_json,
            responsable_id=obj.responsable_id,
            estado=obj.estado,
            creado_en=obj.creado_en,
            dias_para_vencer=obj.dias_para_vencer,
            alerta_vigencia=obj.calcular_alerta_vigencia(umbral_alerta_vigencia),
        )


class ContratoListOut(ContratoOut):
    proveedor_razon_social: str
    proveedor_ruc: str

    @classmethod
    def from_model(cls, obj, umbral_alerta_vigencia: int) -> "ContratoListOut":
        base = ContratoOut.from_model(obj, umbral_alerta_vigencia)
        return cls(
            **base.model_dump(),
            proveedor_razon_social=obj.proveedor.razon_social,
            proveedor_ruc=obj.proveedor.ruc,
        )


class ContratoDetailOut(ContratoListOut):
    cronograma: list[CronogramaEntregaOut]
    productos_contratados: list[ProductoContratadoOut]


class ContratoEstadoUpdate(BaseModel):
    estado: str = Field(description="VIGENTE | SUSPENDIDO | CERRADO")
