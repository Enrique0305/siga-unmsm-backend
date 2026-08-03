from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.receta import receta_repo
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.receta import (
    RecetaCreate,
    RecetaDetailOut,
    RecetaEstadoUpdate,
    RecetaIngredienteOut,
    RecetaOut,
    RecetaValorNutricionalOut,
)

router = APIRouter(prefix="/recetas", tags=["Recetas"])

# Igual que en /alimentos: cualquiera consulta, solo Nutrición/Admin edita.
ROLES_EDICION = ("ADMIN", "NUTRICION")


def _build_detail(receta) -> RecetaDetailOut:
    base = RecetaOut.model_validate(receta)
    return RecetaDetailOut(
        **base.model_dump(),
        ingredientes=[RecetaIngredienteOut.from_model(i) for i in receta.ingredientes],
        valor_nutricional=(
            RecetaValorNutricionalOut.model_validate(receta.valor_nutricional)
            if receta.valor_nutricional
            else None
        ),
    )


@router.get("", response_model=Page[RecetaOut])
async def listar_recetas(
    page: int = 1,
    page_size: int = 20,
    estado: str | None = None,
    categoria_preparacion: str | None = None,
    buscar: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[RecetaOut]:
    items, total = await receta_repo.list_filtrado(
        db, page=page, page_size=page_size, estado=estado, categoria_preparacion=categoria_preparacion, buscar=buscar
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{receta_id}", response_model=RecetaDetailOut)
async def obtener_receta(
    receta_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> RecetaDetailOut:
    receta = await receta_repo.get_con_detalle(db, receta_id)
    if receta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return _build_detail(receta)


@router.post("", response_model=RecetaDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_receta(
    data: RecetaCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RecetaDetailOut:
    try:
        receta = await receta_repo.crear_con_ingredientes(db, data, creado_por_id=current.usuario_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una receta con ese código y versión",
        )

    receta = await receta_repo.get_con_detalle(db, receta.receta_id)
    return _build_detail(receta)


@router.post("/{receta_id}/recalcular-nutricion", response_model=RecetaValorNutricionalOut)
async def recalcular_nutricion(
    receta_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RecetaValorNutricionalOut:
    """Útil cuando el nutricionista corrigió valores del catálogo (RN-26) y se
    quiere refrescar el aporte nutricional de recetas que usan ese alimento."""
    valor = await receta_repo.recalcular_nutricion(db, receta_id)
    await db.commit()
    await db.refresh(valor)
    return valor


@router.patch("/{receta_id}/estado", response_model=RecetaOut)
async def cambiar_estado_receta(
    receta_id: int,
    data: RecetaEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RecetaOut:
    receta = await receta_repo.get_con_detalle(db, receta_id)
    if receta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")

    # RN-23: al salir de BORRADOR, la receta ya debe tener ingredientes y
    # rendimiento > 0 (el rendimiento > 0 ya lo garantiza el CHECK de MySQL
    # desde la creación; aquí se refuerza el mínimo de 1 ingrediente).
    if data.estado != "BORRADOR" and not receta.ingredientes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="RN-23: la receta debe tener al menos un ingrediente antes de avanzar de estado",
        )

    try:
        receta_repo.validar_transicion(receta.estado, data.estado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    receta.estado = data.estado
    if data.estado == "APROBADO":
        receta.aprobado_por_id = current.usuario_id
        receta.aprobado_en = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(receta)
    return receta


@router.post("/{receta_id}/versiones", response_model=RecetaDetailOut, status_code=status.HTTP_201_CREATED)
async def nueva_version_receta(
    receta_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RecetaDetailOut:
    """
    RN-25: crea una copia editable en BORRADOR de una receta APROBADO/
    VIGENTE. La receta original permanece intacta y es la que siguen
    referenciando los menús ya programados.
    """
    try:
        nueva = await receta_repo.crear_nueva_version(db, receta_id, creado_por_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    nueva = await receta_repo.get_con_detalle(db, nueva.receta_id)
    return _build_detail(nueva)
