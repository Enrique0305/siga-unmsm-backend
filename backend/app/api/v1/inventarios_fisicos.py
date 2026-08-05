from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentUser,
    get_current_user,
    require_roles,
    resolver_almacenes_visibles,
    verificar_acceso_almacen,
)
from app.crud.inventario_fisico import inventario_fisico_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.inventario import InventarioFisicoCreate, InventarioFisicoDetailOut, InventarioFisicoOut

router = APIRouter(prefix="/inventarios-fisicos", tags=["Inventario físico"])

ROLES_EDICION = ("ADMIN", "ALMACENERO")


@router.get("", response_model=Page[InventarioFisicoOut])
async def listar_inventarios_fisicos(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[InventarioFisicoOut]:
    if current.acceso_todos_almacenes:
        items, total = await inventario_fisico_repo.list_filtrado(
            db, page=page, page_size=page_size, almacen_id=almacen_id, estado=estado
        )
    else:
        items, total = await inventario_fisico_repo.list_filtrado(
            db, page=page, page_size=page_size, almacen_ids=resolver_almacenes_visibles(current, almacen_id), estado=estado
        )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{inventario_fisico_id}", response_model=InventarioFisicoDetailOut)
async def obtener_inventario_fisico(
    inventario_fisico_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> InventarioFisicoDetailOut:
    inventario = await inventario_fisico_repo.get_con_detalle(db, inventario_fisico_id)
    if inventario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventario físico no encontrado")
    verificar_acceso_almacen(current, inventario.almacen_id)
    return InventarioFisicoDetailOut.from_model(inventario)


@router.post("", response_model=InventarioFisicoDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_inventario_fisico(
    data: InventarioFisicoCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> InventarioFisicoDetailOut:
    """stock_sistema se toma como foto de stock_almacen_producto al momento
    del conteo, nunca lo manda el cliente."""
    verificar_acceso_almacen(current, data.almacen_id)

    inventario = await inventario_fisico_repo.crear(db, data, responsable_id=current.usuario_id)
    await db.commit()

    inventario = await inventario_fisico_repo.get_con_detalle(db, inventario.inventario_fisico_id)
    return InventarioFisicoDetailOut.from_model(inventario)


@router.post("/{inventario_fisico_id}/cerrar", response_model=InventarioFisicoDetailOut)
async def cerrar_inventario_fisico(
    inventario_fisico_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> InventarioFisicoDetailOut:
    """Genera automáticamente un AjusteInventario (y su movimiento de stock)
    por cada línea con diferencia != 0, y cierra el conteo."""
    inventario = await inventario_fisico_repo.get_con_detalle(db, inventario_fisico_id)
    if inventario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventario físico no encontrado")
    verificar_acceso_almacen(current, inventario.almacen_id)

    try:
        await inventario_fisico_repo.cerrar(db, inventario, responsable_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    inventario = await inventario_fisico_repo.get_con_detalle(db, inventario_fisico_id)
    return InventarioFisicoDetailOut.from_model(inventario)
