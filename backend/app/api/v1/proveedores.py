from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_proveedor
from app.crud.proveedor import proveedor_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.proveedor import ProveedorCreate, ProveedorOut, ProveedorUpdate

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])

ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[ProveedorOut])
async def listar_proveedores(
    page: int = 1,
    page_size: int = 20,
    estado: str | None = "ACTIVO",
    buscar: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[ProveedorOut]:
    proveedor_filtro = current.proveedor_id if current.rol == "PROVEEDOR" else None
    items, total = await proveedor_repo.list_filtrado(
        db, page=page, page_size=page_size, estado=estado, buscar=buscar, proveedor_id=proveedor_filtro
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{proveedor_id}", response_model=ProveedorOut)
async def obtener_proveedor(
    proveedor_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> ProveedorOut:
    verificar_acceso_proveedor(current, proveedor_id)
    proveedor = await proveedor_repo.get(db, proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return proveedor


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
async def crear_proveedor(
    data: ProveedorCreate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ProveedorOut:
    try:
        proveedor = await proveedor_repo.create(db, data.model_dump())
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El RUC ya está registrado")

    await db.refresh(proveedor)
    return proveedor


@router.patch("/{proveedor_id}", response_model=ProveedorOut)
async def actualizar_proveedor(
    proveedor_id: int,
    data: ProveedorUpdate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ProveedorOut:
    proveedor = await proveedor_repo.get(db, proveedor_id)
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(proveedor, campo, valor)

    await db.commit()
    await db.refresh(proveedor)
    return proveedor
