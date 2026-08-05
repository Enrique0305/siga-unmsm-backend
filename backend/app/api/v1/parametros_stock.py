from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_current_user,
    require_roles,
    resolver_almacenes_visibles,
    verificar_acceso_almacen,
)
from app.crud.parametro_stock import eliminar, list_filtrado, upsert
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.inventario import AlmacenProductoParametroIn, AlmacenProductoParametroOut

router = APIRouter(prefix="/parametros-stock", tags=["Parámetros de stock por almacén"])

# Mismos roles que PATCH /productos/{id}, dueño del umbral global
# (stock_minimo_referencial) que este override sobreescribe por almacén.
ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[AlmacenProductoParametroOut])
async def listar_parametros(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    producto_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[AlmacenProductoParametroOut]:
    if current.acceso_todos_almacenes:
        items, total = await list_filtrado(
            db, page=page, page_size=page_size, almacen_id=almacen_id, producto_id=producto_id
        )
    else:
        items, total = await list_filtrado(
            db,
            page=page,
            page_size=page_size,
            almacen_ids=resolver_almacenes_visibles(current, almacen_id),
            producto_id=producto_id,
        )
    return Page(
        items=[AlmacenProductoParametroOut.from_model(p) for p in items], total=total, page=page, page_size=page_size
    )


@router.put("", response_model=AlmacenProductoParametroOut)
async def upsert_parametro(
    data: AlmacenProductoParametroIn,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> AlmacenProductoParametroOut:
    """RN-20: defensivo — ADMIN/LOGISTICA_CENTRAL (únicos con permiso de
    escritura aquí) siempre tienen acceso_todos_almacenes=True, así que
    este chequeo nunca bloquea hoy (mismo caso ya documentado en
    ordenes_compra.py, Sesión 11)."""
    verificar_acceso_almacen(current, data.almacen_id)
    try:
        parametro = await upsert(db, data)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.refresh(parametro)
    return AlmacenProductoParametroOut.from_model(parametro)


@router.delete("/{almacen_id}/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_parametro(
    almacen_id: int,
    producto_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> None:
    verificar_acceso_almacen(current, almacen_id)
    eliminado = await eliminar(db, almacen_id, producto_id)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parámetro no encontrado")
    await db.commit()
