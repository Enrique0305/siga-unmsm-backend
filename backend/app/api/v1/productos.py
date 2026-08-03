from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.producto import producto_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.producto import ProductoCreate, ProductoOut, ProductoUpdate

router = APIRouter(prefix="/productos", tags=["Productos (catálogo logístico)"])

# Cualquier usuario autenticado consulta el catálogo (contratos, compras,
# almacén, cocina lo necesitan); solo Logística/Admin lo mantiene.
ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[ProductoOut])
async def listar_productos(
    page: int = 1,
    page_size: int = 20,
    categoria: str | None = None,
    estado: str | None = "ACTIVO",
    buscar: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[ProductoOut]:
    items, total = await producto_repo.list_filtrado(
        db, page=page, page_size=page_size, categoria=categoria, estado=estado, buscar=buscar
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{producto_id}", response_model=ProductoOut)
async def obtener_producto(
    producto_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> ProductoOut:
    producto = await producto_repo.get(db, producto_id)
    if producto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return producto


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
async def crear_producto(
    data: ProductoCreate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ProductoOut:
    try:
        producto = await producto_repo.create(db, data.model_dump())
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de producto ya existe")

    await db.refresh(producto)
    return producto


@router.patch("/{producto_id}", response_model=ProductoOut)
async def actualizar_producto(
    producto_id: int,
    data: ProductoUpdate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ProductoOut:
    producto = await producto_repo.get(db, producto_id)
    if producto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(producto, campo, valor)

    await db.commit()
    await db.refresh(producto)
    return producto
