from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sistema import ParametroSistema
from app.schemas.sistema import ParametroSistemaIn


async def list_todos(db: AsyncSession) -> list[ParametroSistema]:
    stmt = select(ParametroSistema).order_by(ParametroSistema.clave)
    return list((await db.execute(stmt)).scalars().all())


async def obtener(db: AsyncSession, clave: str) -> ParametroSistema | None:
    return await db.get(ParametroSistema, clave)


async def obtener_entero(db: AsyncSession, clave: str, default: int) -> int:
    """Nunca lanza: si la clave no existe o su valor no castea a entero,
    devuelve `default` (el llamador no necesita manejar ningún caso de
    error, solo elegir un valor de respaldo sensato)."""
    parametro = await obtener(db, clave)
    if parametro is None:
        return default
    try:
        return int(parametro.valor)
    except ValueError:
        return default


async def upsert(db: AsyncSession, data: ParametroSistemaIn, actualizado_por_id: int) -> ParametroSistema:
    existente = await db.get(ParametroSistema, data.clave)
    if existente is not None:
        existente.valor = data.valor
        existente.descripcion = data.descripcion
        existente.actualizado_por_id = actualizado_por_id
        await db.flush()
        return existente

    parametro = ParametroSistema(
        clave=data.clave,
        valor=data.valor,
        descripcion=data.descripcion,
        actualizado_por_id=actualizado_por_id,
    )
    db.add(parametro)
    await db.flush()
    return parametro


async def eliminar(db: AsyncSession, clave: str) -> bool:
    parametro = await db.get(ParametroSistema, clave)
    if parametro is None:
        return False
    await db.delete(parametro)
    await db.flush()
    return True
