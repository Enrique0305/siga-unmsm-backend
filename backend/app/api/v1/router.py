from fastapi import APIRouter

from app.api.v1 import alimentos, almacenes, auth, catalogos, planificacion, recetas, usuarios

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(almacenes.router)
api_router.include_router(catalogos.router)
api_router.include_router(alimentos.router)
api_router.include_router(recetas.router)
api_router.include_router(planificacion.router)

# A medida que se implementen los siguientes módulos del diseño
# (Contratos, Órdenes de Compra, Inspección/Actas, Kardex/Bin Card,
# Cocina/Consumo, Conformidad/Pago), sus routers se agregan aquí, cada
# uno en su propio archivo app/api/v1/<modulo>.py, siguiendo el mismo
# patrón de esta carpeta.
