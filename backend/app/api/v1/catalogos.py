from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.catalogos import CategoriaAlimento, UnidadMedida
from app.models.organizacion import CentroConsumo, Rol, Sede
from app.schemas.alimento import CategoriaAlimentoOut
from app.schemas.almacen import CentroConsumoOut, SedeOut
from app.schemas.usuario import RolOut

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


@router.get("/categorias-alimento", response_model=list[CategoriaAlimentoOut])
async def listar_categorias_alimento(
    db: AsyncSession = Depends(get_db),
    _current=Depends(get_current_user),
) -> list[CategoriaAlimento]:
    stmt = select(CategoriaAlimento).order_by(CategoriaAlimento.nombre)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/unidades-medida")
async def listar_unidades_medida(
    db: AsyncSession = Depends(get_db),
    _current=Depends(get_current_user),
) -> list[dict]:
    stmt = select(UnidadMedida).order_by(UnidadMedida.codigo)
    unidades = (await db.execute(stmt)).scalars().all()
    return [{"unidad_id": u.unidad_id, "codigo": u.codigo, "nombre": u.nombre} for u in unidades]


@router.get("/sedes", response_model=list[SedeOut])
async def listar_sedes(
    db: AsyncSession = Depends(get_db),
    _current=Depends(get_current_user),
) -> list[Sede]:
    stmt = select(Sede).order_by(Sede.nombre)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/centros-consumo", response_model=list[CentroConsumoOut])
async def listar_centros_consumo(
    sede_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    _current=Depends(get_current_user),
) -> list[CentroConsumo]:
    stmt = select(CentroConsumo).order_by(CentroConsumo.nombre)
    if sede_id is not None:
        stmt = stmt.where(CentroConsumo.sede_id == sede_id)
    return list((await db.execute(stmt)).scalars().all())


@router.get("/roles", response_model=list[RolOut])
async def listar_roles(
    db: AsyncSession = Depends(get_db),
    _current=Depends(get_current_user),
) -> list[Rol]:
    stmt = select(Rol).order_by(Rol.nombre)
    return list((await db.execute(stmt)).scalars().all())
