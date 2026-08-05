from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles
from app.crud.notificacion import notificacion_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.notificacion import NotificacionOut

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])

# RN-12: "Notificación a Logística" — mismos roles que ROLES_LECTURA de
# reportes.py, es a quien está dirigida la alerta de contrato.
ROLES_LECTURA = ("ADMIN", "LOGISTICA_CENTRAL")


@router.get("", response_model=Page[NotificacionOut])
async def listar_notificaciones(
    page: int = 1,
    page_size: int = 20,
    leida: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_LECTURA)),
) -> Page[NotificacionOut]:
    items, total = await notificacion_repo.list_filtrado(db, page=page, page_size=page_size, leida=leida)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.patch("/{notificacion_id}/leida", response_model=NotificacionOut)
async def marcar_notificacion_leida(
    notificacion_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_LECTURA)),
) -> NotificacionOut:
    notificacion = await notificacion_repo.marcar_leida(db, notificacion_id)
    if notificacion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notificación no encontrada")
    await db.commit()
    return notificacion
