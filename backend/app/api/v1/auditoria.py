from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.crud.auditoria import auditoria_repo
from app.db.session import get_db
from app.schemas.auditoria import AuditoriaLogOut
from app.schemas.common import Page

router = APIRouter(prefix="/auditoria", tags=["Auditoría"])

# Mismos roles que el gate de frontend/lib/nav.ts para "/reportes" (esta
# pantalla vive ahí, pestaña "Auditoría").
ROLES_LECTURA = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[AuditoriaLogOut])
async def listar_auditoria(
    page: int = 1,
    page_size: int = 20,
    entidad: str | None = None,
    entidad_id: int | None = None,
    usuario_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_LECTURA)),
) -> Page[AuditoriaLogOut]:
    """Línea de tiempo de un documento (RN-08): filtrar por `entidad`
    (nombre de tabla, ej. `contrato`) + `entidad_id` para ver su historial."""
    items, total = await auditoria_repo.list_filtrado(
        db, page=page, page_size=page_size, entidad=entidad, entidad_id=entidad_id, usuario_id=usuario_id
    )
    return Page(items=items, total=total, page=page, page_size=page_size)
