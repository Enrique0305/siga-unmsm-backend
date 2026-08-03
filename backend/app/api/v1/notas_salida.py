from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_almacen
from app.crud.nota_salida import nota_salida_repo
from app.crud.solicitud_cocina import solicitud_cocina_repo
from app.db.session import get_db
from app.schemas.cocina import NotaSalidaCreate, NotaSalidaDetailOut, NotaSalidaOut
from app.schemas.common import Page

router = APIRouter(prefix="/notas-salida", tags=["Notas de salida"])

# "[Almacenero] aprueba y emite Nota de Salida de Almacén" (docs sección 4.4)
ROLES_EDICION = ("ADMIN", "ALMACENERO")


@router.get("", response_model=Page[NotaSalidaOut])
async def listar_notas_salida(
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    solicitud_cocina_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[NotaSalidaOut]:
    items, total = await nota_salida_repo.list_filtrado(
        db, page=page, page_size=page_size, almacen_id=almacen_id, solicitud_cocina_id=solicitud_cocina_id
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{nota_salida_id}", response_model=NotaSalidaDetailOut)
async def obtener_nota_salida(
    nota_salida_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> NotaSalidaDetailOut:
    nota = await nota_salida_repo.get_con_detalle(db, nota_salida_id)
    if nota is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nota de salida no encontrada")
    return NotaSalidaDetailOut.from_model(nota)


@router.post("", response_model=NotaSalidaDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_nota_salida(
    data: NotaSalidaCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> NotaSalidaDetailOut:
    """RN-17 (descuenta solo el almacén de la solicitud) · RN-07 (nunca
    despacha más de lo solicitado/reservado). Libera stock_comprometido y
    registra la salida real en kardex (RN-06)."""
    solicitud = await solicitud_cocina_repo.get(db, data.solicitud_cocina_id)
    if solicitud is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="La solicitud de cocina indicada no existe")
    verificar_acceso_almacen(current, solicitud.almacen_id)

    try:
        nota = await nota_salida_repo.crear(db, data, almacenero_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de nota de salida ya existe")

    nota = await nota_salida_repo.get_con_detalle(db, nota.nota_salida_id)
    return NotaSalidaDetailOut.from_model(nota)
