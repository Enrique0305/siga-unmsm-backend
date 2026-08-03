from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.informe_conformidad import informe_conformidad_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.pagos import (
    InformeConformidadPagoCreate,
    InformeConformidadPagoDetailOut,
    InformeConformidadPagoOut,
    InformeEstadoUpdate,
)

router = APIRouter(prefix="/informes-conformidad-pago", tags=["Informes de conformidad para pago"])

# "[Logística] deriva a Oficina de Abastecimiento" (docs sección 4.5) — genera el informe
ROLES_GENERAR = ("ADMIN", "LOGISTICA_CENTRAL")
# Oficina de Abastecimiento mueve el informe por sus estados de pago
ROLES_ESTADO = ("ADMIN", "PAGOS")


@router.get("", response_model=Page[InformeConformidadPagoOut])
async def listar_informes(
    page: int = 1,
    page_size: int = 20,
    orden_compra_id: int | None = None,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[InformeConformidadPagoOut]:
    items, total = await informe_conformidad_repo.list_filtrado(
        db, page=page, page_size=page_size, orden_compra_id=orden_compra_id, estado=estado
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{informe_id}", response_model=InformeConformidadPagoDetailOut)
async def obtener_informe(
    informe_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> InformeConformidadPagoDetailOut:
    informe = await informe_conformidad_repo.get_con_detalle(db, informe_id)
    if informe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Informe de conformidad no encontrado")
    return InformeConformidadPagoDetailOut.from_model(informe)


@router.post("", response_model=InformeConformidadPagoDetailOut, status_code=status.HTTP_201_CREATED)
async def generar_informe(
    data: InformeConformidadPagoCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_GENERAR)),
) -> InformeConformidadPagoDetailOut:
    """Solo sobre una OC ya CERRADO/PENALIZADO, una vez por OC. Recalcula
    conforme/retenido por línea (RN-05) y suma las Penalidad ya registradas."""
    try:
        informe = await informe_conformidad_repo.generar_informe(db, data, generado_por_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de informe ya existe")

    informe = await informe_conformidad_repo.get_con_detalle(db, informe.informe_id)
    return InformeConformidadPagoDetailOut.from_model(informe)


@router.patch("/{informe_id}/estado", response_model=InformeConformidadPagoOut)
async def cambiar_estado_informe(
    informe_id: int,
    data: InformeEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_ESTADO)),
) -> InformeConformidadPagoOut:
    """ENVIADO -> RECIBIDO -> EN_PROCESO_DE_PAGO -> PAGADO | DEVUELTO."""
    informe = await informe_conformidad_repo.get(db, informe_id)
    if informe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Informe de conformidad no encontrado")

    try:
        await informe_conformidad_repo.cambiar_estado(db, informe, data.estado)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.commit()
    await db.refresh(informe)
    return informe
