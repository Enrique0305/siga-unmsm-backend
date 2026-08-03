from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.catalogos import CategoriaAlimento, UnidadMedida
from app.schemas.alimento import CategoriaAlimentoOut

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
