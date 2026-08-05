from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, resolver_almacenes_visibles
from app.crud.almacen import almacen_repo
from app.db.session import get_db
from app.schemas.almacen import AlmacenCreate, AlmacenOut, AlmacenUpdate
from app.schemas.common import Page

router = APIRouter(prefix="/almacenes", tags=["Almacenes"])


@router.get("", response_model=Page[AlmacenOut])
async def listar_almacenes(
    page: int = 1,
    page_size: int = 20,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[AlmacenOut]:
    """
    RN-20: si el usuario no tiene acceso_todos_almacenes, solo ve los
    almacenes de su lista de autorización.
    """
    if current.acceso_todos_almacenes:
        items, total = await almacen_repo.list_filtrado(db, page=page, page_size=page_size, estado=estado)
    else:
        items, total = await almacen_repo.list_filtrado(
            db, page=page, page_size=page_size, estado=estado, almacen_ids=current.almacenes
        )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{almacen_id}", response_model=AlmacenOut)
async def obtener_almacen(
    almacen_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> AlmacenOut:
    if not current.tiene_acceso_almacen(almacen_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin autorización sobre este almacén")
    almacen = await almacen_repo.get(db, almacen_id)
    if almacen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")
    return almacen


@router.post("", response_model=AlmacenOut, status_code=status.HTTP_201_CREATED)
async def crear_almacen(
    data: AlmacenCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles("ADMIN", "LOGISTICA_CENTRAL")),
) -> AlmacenOut:
    try:
        almacen = await almacen_repo.create(db, data.model_dump())
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de almacén ya existe")
    return almacen


@router.patch("/{almacen_id}", response_model=AlmacenOut)
async def actualizar_almacen(
    almacen_id: int,
    data: AlmacenUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles("ADMIN", "LOGISTICA_CENTRAL")),
) -> AlmacenOut:
    almacen = await almacen_repo.get(db, almacen_id)
    if almacen is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(almacen, field, value)
    await db.commit()
    await db.refresh(almacen)
    return almacen
