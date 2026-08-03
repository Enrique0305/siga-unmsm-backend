from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.inspeccion import inspeccion_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.inspeccion import InspeccionCreate, InspeccionDetailOut, InspeccionOut

router = APIRouter(prefix="/inspecciones", tags=["Inspección"])

# "[Inspector] realiza Inspección de calidad y cantidad por línea de producto" (docs sección 4.3)
ROLES_EDICION = ("ADMIN", "INSPECTOR")


@router.get("", response_model=Page[InspeccionOut])
async def listar_inspecciones(
    page: int = 1,
    page_size: int = 20,
    guia_remision_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[InspeccionOut]:
    items, total = await inspeccion_repo.list_filtrado(db, page=page, page_size=page_size, guia_remision_id=guia_remision_id)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{inspeccion_id}", response_model=InspeccionDetailOut)
async def obtener_inspeccion(
    inspeccion_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> InspeccionDetailOut:
    inspeccion = await inspeccion_repo.get_con_detalle(db, inspeccion_id)
    if inspeccion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspección no encontrada")
    return InspeccionDetailOut.from_model(inspeccion)


@router.post("", response_model=InspeccionDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_inspeccion(
    data: InspeccionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> InspeccionDetailOut:
    """Cada línea de guía solo puede inspeccionarse una vez; la suma
    conforme+observada debe igualar lo entregado. Recalcula
    guia_remision.estado (PENDIENTE -> PARCIAL -> CONFORME/OBSERVADO)."""
    try:
        inspeccion = await inspeccion_repo.crear(db, data, inspector_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    inspeccion = await inspeccion_repo.get_con_detalle(db, inspeccion.inspeccion_id)
    return InspeccionDetailOut.from_model(inspeccion)
