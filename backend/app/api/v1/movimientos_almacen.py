from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_roles, verificar_acceso_almacen
from app.crud.movimiento_simple import crear_ajuste, crear_devolucion, crear_merma
from app.db.session import get_db
from app.schemas.inventario import (
    AjusteInventarioCreate,
    AjusteInventarioOut,
    DevolucionCreate,
    DevolucionOut,
    MermaCreate,
    MermaOut,
)

router = APIRouter(tags=["Ajustes, mermas y devoluciones"])

ROLES_EDICION = ("ADMIN", "ALMACENERO")


@router.post("/ajustes-inventario", response_model=AjusteInventarioOut, status_code=status.HTTP_201_CREATED)
async def crear_ajuste_inventario(
    data: AjusteInventarioCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> AjusteInventarioOut:
    verificar_acceso_almacen(current, data.almacen_id)
    try:
        ajuste = await crear_ajuste(db, data, responsable_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.refresh(ajuste)
    return AjusteInventarioOut.from_model(ajuste)


@router.post("/mermas", response_model=MermaOut, status_code=status.HTTP_201_CREATED)
async def crear_merma_almacen(
    data: MermaCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> MermaOut:
    verificar_acceso_almacen(current, data.almacen_id)
    try:
        merma = await crear_merma(db, data, responsable_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.refresh(merma)
    return MermaOut.from_model(merma)


@router.post("/devoluciones", response_model=DevolucionOut, status_code=status.HTTP_201_CREATED)
async def crear_devolucion_almacen(
    data: DevolucionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> DevolucionOut:
    verificar_acceso_almacen(current, data.almacen_id)
    try:
        devolucion = await crear_devolucion(db, data, responsable_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await db.refresh(devolucion)
    return DevolucionOut.from_model(devolucion)
