from fastapi import APIRouter

from app.api.v1 import (
    actas_observacion,
    alimentos,
    almacenes,
    auth,
    catalogos,
    contratos,
    guias_remision,
    ingresos_almacen,
    inspecciones,
    inventarios_fisicos,
    movimientos_almacen,
    ordenes_compra,
    pedidos_semanales,
    planificacion,
    productos,
    proveedores,
    recetas,
    requerimientos,
    stock,
    transferencias_almacen,
    ubicaciones,
    usuarios,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(almacenes.router)
api_router.include_router(catalogos.router)
api_router.include_router(alimentos.router)
api_router.include_router(recetas.router)
api_router.include_router(planificacion.router)
api_router.include_router(productos.router)
api_router.include_router(requerimientos.router)
api_router.include_router(proveedores.router)
api_router.include_router(contratos.router)
api_router.include_router(ordenes_compra.router)
api_router.include_router(pedidos_semanales.router)
api_router.include_router(guias_remision.router)
api_router.include_router(inspecciones.router)
api_router.include_router(actas_observacion.router)
api_router.include_router(ubicaciones.router)
api_router.include_router(ingresos_almacen.router)
api_router.include_router(stock.router)
api_router.include_router(movimientos_almacen.router)
api_router.include_router(inventarios_fisicos.router)
api_router.include_router(transferencias_almacen.router)

# A medida que se implementen los siguientes módulos del diseño (Cocina/
# Consumo, Conformidad/Pago), sus routers se agregan aquí, cada uno en su
# propio archivo app/api/v1/<modulo>.py, siguiendo el mismo patrón de esta
# carpeta.
