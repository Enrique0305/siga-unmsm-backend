from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.planificacion import MenuDia, MenuQuincenal, Plato, RacionAnual
from app.models.receta import Receta


class CRUDMenuDia(CRUDBase[MenuDia]):
    async def get_con_platos(self, db: AsyncSession, menu_dia_id: int) -> MenuDia | None:
        stmt = (
            select(MenuDia)
            .where(MenuDia.menu_dia_id == menu_dia_id)
            .options(selectinload(MenuDia.platos).selectinload(Plato.receta))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def agregar_plato(self, db: AsyncSession, menu_dia_id: int, receta_id: int, raciones_override: int | None) -> Plato:
        """RN-22: solo recetas en estado VIGENTE pueden incorporarse a un menú."""
        receta = await db.get(Receta, receta_id)
        if receta is None:
            raise ValueError("Receta no encontrada")
        if receta.estado != "VIGENTE":
            raise ValueError(f"RN-22: la receta '{receta.nombre}' no está VIGENTE (estado actual: {receta.estado})")

        plato = Plato(menu_dia_id=menu_dia_id, receta_id=receta_id, raciones_override=raciones_override)
        db.add(plato)
        await db.flush()
        await db.refresh(plato, attribute_names=["receta"])
        return plato


menu_dia_repo = CRUDMenuDia(MenuDia)
racion_anual_repo = CRUDBase(RacionAnual)
menu_quincenal_repo = CRUDBase(MenuQuincenal)
