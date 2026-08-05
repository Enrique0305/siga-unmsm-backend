from datetime import date, datetime

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


class BomConsolidadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bom_consolidado_id: int
    racion_anual_id: int
    tipo_periodo: str
    periodo_inicio: date
    periodo_fin: date
    almacen_id: int
    almacen_codigo: str
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    cantidad_requerida_total: float
    stock_disponible_referencia: float | None
    saldo_contractual_referencia: float | None
    estado_suficiencia: str | None
    generado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "BomConsolidadoOut":
        return cls(
            bom_consolidado_id=obj.bom_consolidado_id,
            racion_anual_id=obj.racion_anual_id,
            tipo_periodo=obj.tipo_periodo,
            periodo_inicio=obj.periodo_inicio,
            periodo_fin=obj.periodo_fin,
            almacen_id=obj.almacen_id,
            almacen_codigo=obj.almacen.codigo,
            producto_id=obj.producto_id,
            producto_codigo=obj.producto.codigo,
            producto_nombre=obj.producto.nombre,
            cantidad_requerida_total=obj.cantidad_requerida_total,
            stock_disponible_referencia=obj.stock_disponible_referencia,
            saldo_contractual_referencia=obj.saldo_contractual_referencia,
            estado_suficiencia=obj.estado_suficiencia,
            generado_en=obj.generado_en,
        )
