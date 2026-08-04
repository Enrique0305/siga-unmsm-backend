from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.planificacion import MenuDia, MenuQuincenal, Plato, RacionAnual
from app.models.receta import Receta

TRANSICIONES_VALIDAS_RACION: dict[str, set[str]] = {
    "BORRADOR": {"APROBADO"},
    "APROBADO": set(),
}

TRANSICIONES_VALIDAS_MENU: dict[str, set[str]] = {
    "BORRADOR": {"EN_REVISION"},
    "EN_REVISION": {"APROBADO", "BORRADOR"},
    "APROBADO": {"VIGENTE"},
    "VIGENTE": {"HISTORICO"},
    "HISTORICO": set(),
}


class CRUDRacionAnual(CRUDBase[RacionAnual]):
    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS_RACION.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    def aplicar_transicion(self, racion: RacionAnual, estado_nuevo: str) -> None:
        racion.estado = estado_nuevo


class CRUDMenuQuincenal(CRUDBase[MenuQuincenal]):
    async def get_con_dias(self, db: AsyncSession, menu_id: int) -> MenuQuincenal | None:
        stmt = (
            select(MenuQuincenal)
            .where(MenuQuincenal.menu_id == menu_id)
            .options(selectinload(MenuQuincenal.dias))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS_MENU.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    def aplicar_transicion(self, menu: MenuQuincenal, estado_nuevo: str, aprobado_por_id: int) -> None:
        menu.estado = estado_nuevo
        if estado_nuevo == "APROBADO":
            menu.aprobado_por_id = aprobado_por_id
            menu.aprobado_en = datetime.now(timezone.utc)


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
racion_anual_repo = CRUDRacionAnual(RacionAnual)
menu_quincenal_repo = CRUDMenuQuincenal(MenuQuincenal)
