from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.penalidad import penalidad_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.pagos import PenalidadCreate, PenalidadOut

router = APIRouter(prefix="/penalidades", tags=["Penalidades"])

ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[PenalidadOut])
async def listar_penalidades(
    page: int = 1,
    page_size: int = 20,
    orden_compra_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[PenalidadOut]:
    items, total = await penalidad_repo.list_filtrado(db, page=page, page_size=page_size, orden_compra_id=orden_compra_id)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=PenalidadOut, status_code=status.HTTP_201_CREATED)
async def crear_penalidad(
    data: PenalidadCreate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> PenalidadOut:
    """Penalidad manual (no ligada a una observación de calidad, ej. atraso de
    entrega). Bloqueada si la OC ya tiene un informe de conformidad generado."""
    try:
        penalidad = await penalidad_repo.crear_manual(db, data)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.refresh(penalidad)
    return penalidad
