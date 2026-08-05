from fastapi import APIRouter

from app.api.v1 import (
    actas_observacion,
    alimentos,
    almacenes,
    auditoria,
    auth,
    catalogos,
    contratos,
    guias_remision,
    informes_conformidad,
    ingresos_almacen,
    inspecciones,
    inventarios_fisicos,
    movimientos_almacen,
    notas_salida,
    ordenes_compra,
    parametros_stock,
    pedidos_semanales,
    penalidades,
    planificacion,
    productos,
    proveedores,
    recetas,
    reportes,
    requerimientos,
    solicitudes_cocina,
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
api_router.include_router(parametros_stock.router)
api_router.include_router(movimientos_almacen.router)
api_router.include_router(inventarios_fisicos.router)
api_router.include_router(transferencias_almacen.router)
api_router.include_router(solicitudes_cocina.router)
api_router.include_router(notas_salida.router)
api_router.include_router(penalidades.router)
api_router.include_router(informes_conformidad.router)
api_router.include_router(auditoria.router)
api_router.include_router(reportes.router)

# Backend completo (Módulos 1 a 5 + Reportes/auditoría transversal,
# sección 10 de CLAUDE.md). Queda pendiente el Frontend Next.js.
