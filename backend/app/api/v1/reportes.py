from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.crud.reportes import alertas_almacen, comparativo_consumo, valorizacion_inventario
from app.db.session import get_db
from app.schemas.reportes import AlertasAlmacenOut, ComparativoConsumoOut, ValorizacionAlmacenOut

router = APIRouter(prefix="/reportes", tags=["Reportes"])

# Reportes agregados de todo el sistema — a diferencia de catálogos de uso
# transversal (ej. GET /productos), aquí no hay nada que ALMACENERO/COCINA/
# etc. deban ver, así que se protege también la lectura (mismos roles que
# el gate de frontend/lib/nav.ts para "/reportes").
ROLES_LECTURA = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("/valorizacion-inventario", response_model=list[ValorizacionAlmacenOut])
async def reporte_valorizacion_inventario(
    almacen_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_LECTURA)),
) -> list[ValorizacionAlmacenOut]:
    filas = await valorizacion_inventario(db, almacen_id=almacen_id)
    return [ValorizacionAlmacenOut(**f) for f in filas]


@router.get("/comparativo-consumo", response_model=ComparativoConsumoOut)
async def reporte_comparativo_consumo(
    producto_id: int,
    fecha_inicio: date,
    fecha_fin: date,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_LECTURA)),
) -> ComparativoConsumoOut:
    """Teórico (BOM, Módulo 1A) vs. comprado (Módulo 3) vs. recibido
    (Almacén) vs. despachado (Módulo 4), para un producto y rango de fechas."""
    try:
        resultado = await comparativo_consumo(db, producto_id, fecha_inicio, fecha_fin)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ComparativoConsumoOut(**resultado)


@router.get("/alertas", response_model=AlertasAlmacenOut)
async def reporte_alertas(
    almacen_id: int | None = None,
    dias_vencimiento: int = 30,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_LECTURA)),
) -> AlertasAlmacenOut:
    """Stock bajo (vs. producto.stock_minimo_referencial), próximos a vencer
    (guia_remision_detalle.fecha_vencimiento de líneas ya ingresadas) y
    líneas OBSERVADO sin acta resuelta."""
    resultado = await alertas_almacen(db, almacen_id=almacen_id, dias_vencimiento=dias_vencimiento)
    return AlertasAlmacenOut(**resultado)
