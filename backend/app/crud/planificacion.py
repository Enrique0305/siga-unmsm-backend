from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.planificacion import MenuDia, MenuQuincenal, Plato, RacionAnual
from app.models.receta import Receta

# selectinload compartido por get_con_platos/get_menu_diario/get_menu_semanal:
# platos -> receta -> valor_nutricional, para poder sumar el aporte
# nutricional por dia/servicio sin lazy-load (gotcha async #1).
_CARGA_PLATOS_CON_NUTRICION = selectinload(MenuDia.platos).selectinload(Plato.receta).selectinload(
    Receta.valor_nutricional
)

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
            .options(_CARGA_PLATOS_CON_NUTRICION)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_menu_diario(self, db: AsyncSession, fecha: date, centro_consumo_id: int) -> list[MenuDia]:
        """Menú(s) de un día para un centro de consumo — uno por tipo_servicio (DESAYUNO/ALMUERZO/CENA).

        Solo mira el MenuQuincenal VIGENTE: un BORRADOR/EN_REVISION todavía
        puede cambiar, así que no es "el menú" real de ese día para quien
        consume este endpoint desde afuera.
        """
        stmt = (
            select(MenuDia)
            .join(MenuQuincenal, MenuDia.menu_id == MenuQuincenal.menu_id)
            .join(RacionAnual, MenuQuincenal.racion_anual_id == RacionAnual.racion_anual_id)
            .where(
                MenuDia.fecha == fecha,
                RacionAnual.centro_consumo_id == centro_consumo_id,
                MenuQuincenal.estado == "VIGENTE",
            )
            .options(_CARGA_PLATOS_CON_NUTRICION)
        )
        return list((await db.execute(stmt)).scalars().all())

    async def get_menu_semanal(self, db: AsyncSession, fecha_inicio: date, centro_consumo_id: int) -> list[MenuDia]:
        """Los días de menú de una semana (fecha_inicio .. fecha_inicio+6) para
        un centro de consumo, en orden. Mismo criterio que get_menu_diario:
        solo MenuQuincenal VIGENTE.
        """
        fecha_fin = fecha_inicio + timedelta(days=6)
        stmt = (
            select(MenuDia)
            .join(MenuQuincenal, MenuDia.menu_id == MenuQuincenal.menu_id)
            .join(RacionAnual, MenuQuincenal.racion_anual_id == RacionAnual.racion_anual_id)
            .where(
                MenuDia.fecha.between(fecha_inicio, fecha_fin),
                RacionAnual.centro_consumo_id == centro_consumo_id,
                MenuQuincenal.estado == "VIGENTE",
            )
            .options(_CARGA_PLATOS_CON_NUTRICION)
            .order_by(MenuDia.fecha)
        )
        # tipo_servicio es texto libre (DESAYUNO/ALMUERZO/CENA) -- ordenar
        # alfabeticamente lo dejaria ALMUERZO antes que DESAYUNO, asi que el
        # orden por servicio dentro de cada dia se resuelve en Python.
        orden_servicio = {"DESAYUNO": 0, "ALMUERZO": 1, "CENA": 2}
        items = list((await db.execute(stmt)).scalars().all())
        items.sort(key=lambda dia: (dia.fecha, orden_servicio.get(dia.tipo_servicio, 99)))
        return items

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
