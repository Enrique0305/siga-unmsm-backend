from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.ingreso_almacen import ingreso_almacen_repo
from app.db.session import get_db
from app.models.compras import GuiaRemision
from app.schemas.common import Page
from app.schemas.inventario import IngresoAlmacenCreate, IngresoAlmacenDetailOut, IngresoAlmacenOut

router = APIRouter(prefix="/ingresos-almacen", tags=["Ingresos a almacén"])

ROLES_EDICION = ("ADMIN", "ALMACENERO")


@router.get("", response_model=Page[IngresoAlmacenOut])
async def listar_ingresos(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    guia_remision_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[IngresoAlmacenOut]:
    items, total = await ingreso_almacen_repo.list_filtrado(
        db, page=page, page_size=page_size, almacen_id=almacen_id, guia_remision_id=guia_remision_id
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ingreso_almacen_id}", response_model=IngresoAlmacenDetailOut)
async def obtener_ingreso(
    ingreso_almacen_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> IngresoAlmacenDetailOut:
    ingreso = await ingreso_almacen_repo.get_con_detalle(db, ingreso_almacen_id)
    if ingreso is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingreso a almacén no encontrado")
    return IngresoAlmacenDetailOut.from_model(ingreso)


@router.post("", response_model=IngresoAlmacenDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_ingreso(
    data: IngresoAlmacenCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> IngresoAlmacenDetailOut:
    """RN-04: convierte lo CONFORME de una inspección en stock real. El
    almacén se deriva de guia_remision.almacen_destino_id (RN-20 se valida
    contra ese almacén, no contra uno que mande el cliente)."""
    guia = await db.get(GuiaRemision, data.guia_remision_id)
    if guia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La guía de remisión indicada no existe")
    verificar_acceso_almacen(current, guia.almacen_destino_id)

    try:
        ingreso = await ingreso_almacen_repo.crear(db, data, almacenero_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de ingreso ya existe")

    ingreso = await ingreso_almacen_repo.get_con_detalle(db, ingreso.ingreso_almacen_id)
    return IngresoAlmacenDetailOut.from_model(ingreso)
