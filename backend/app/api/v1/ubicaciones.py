from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.ubicacion import ubicacion_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.ubicacion import UbicacionInternaCreate, UbicacionInternaOut

router = APIRouter(prefix="/ubicaciones", tags=["Ubicaciones internas"])

ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL", "ALMACENERO")


@router.get("", response_model=Page[UbicacionInternaOut])
async def listar_ubicaciones(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[UbicacionInternaOut]:
    items, total = await ubicacion_repo.list_filtrado(db, page=page, page_size=page_size, almacen_id=almacen_id)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=UbicacionInternaOut, status_code=status.HTTP_201_CREATED)
async def crear_ubicacion(
    data: UbicacionInternaCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> UbicacionInternaOut:
    verificar_acceso_almacen(current, data.almacen_id)
    try:
        ubicacion = await ubicacion_repo.create(db, data.model_dump())
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una ubicación con esa combinación de zona/estante/nivel/contenedor en este almacén",
        )

    await db.refresh(ubicacion)
    return ubicacion
