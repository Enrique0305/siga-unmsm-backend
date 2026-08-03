from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dosificacion import DosificacionDetalle
from app.models.organizacion import CentroConsumo
from app.models.planificacion import MenuDia, Plato
from app.models.receta import RecetaIngrediente


class ServicioDosificacion:
    """
    Explosión de materiales automática (Módulo 1A, sección 4.1A):

        cantidad_requerida = cantidad_ingrediente_receta
                              × (raciones_programadas / numero_raciones_base)
                              × (1 + merma_pct/100)

    Los ingredientes de la receta (receta_ingrediente.cantidad_bruta_g /
    cantidad_neta_g) están definidos para preparar numero_raciones_base
    raciones; se escalan linealmente a las raciones realmente programadas
    para ese día/comedor/almacén. El factor de rendimiento de la receta ya
    fue aplicado por el nutricionista al definir cantidad_bruta vs.
    cantidad_neta, por eso no se vuelve a aplicar aquí — evita duplicar el
    ajuste. Este criterio de escalado se deja documentado explícitamente
    para que el nutricionista lo valide o ajuste.
    """

    async def calcular_dia(
        self,
        db: AsyncSession,
        menu_dia_id: int,
        centro_consumo_id: int,
    ) -> list[DosificacionDetalle]:
        centro = await db.get(CentroConsumo, centro_consumo_id)
        if centro is None:
            raise ValueError("Centro de consumo no encontrado")

        stmt = (
            select(MenuDia)
            .where(MenuDia.menu_dia_id == menu_dia_id)
            .options(selectinload(MenuDia.platos).selectinload(Plato.receta))
        )
        menu_dia = (await db.execute(stmt)).scalar_one_or_none()
        if menu_dia is None:
            raise ValueError("Día de menú no encontrado")
        if not menu_dia.platos:
            raise ValueError("Este día de menú no tiene platos asignados todavía")

        # Idempotente: recalcular reemplaza el cálculo previo de este día+comedor
        await db.execute(
            delete(DosificacionDetalle).where(
                DosificacionDetalle.menu_dia_id == menu_dia_id,
                DosificacionDetalle.centro_consumo_id == centro_consumo_id,
            )
        )

        resultado: list[DosificacionDetalle] = []
        for plato in menu_dia.platos:
            receta = plato.receta
            raciones = plato.raciones_override or menu_dia.raciones_programadas
            factor_escala = raciones / receta.numero_raciones_base

            stmt_ing = select(RecetaIngrediente).where(RecetaIngrediente.receta_id == receta.receta_id)
            ingredientes = (await db.execute(stmt_ing)).scalars().all()

            for ing in ingredientes:
                merma_factor = 1 + (ing.merma_pct / 100.0)
                fila = DosificacionDetalle(
                    menu_dia_id=menu_dia_id,
                    plato_id=plato.plato_id,
                    receta_id=receta.receta_id,
                    centro_consumo_id=centro_consumo_id,
                    almacen_id=centro.almacen_id,
                    alimento_id=ing.alimento_id,
                    raciones_programadas=raciones,
                    cantidad_bruta_requerida=round(ing.cantidad_bruta_g * factor_escala * merma_factor, 4),
                    cantidad_neta_requerida=round(ing.cantidad_neta_g * factor_escala, 4),
                )
                db.add(fila)
                resultado.append(fila)

        await db.flush()
        # recarga con alimento para la respuesta (codigo/nombre)
        ids = [f.dosificacion_id for f in resultado]
        stmt_out = (
            select(DosificacionDetalle)
            .where(DosificacionDetalle.dosificacion_id.in_(ids))
            .options(selectinload(DosificacionDetalle.alimento))
        )
        return list((await db.execute(stmt_out)).scalars().all())

    async def consolidar_por_almacen(
        self, db: AsyncSession, menu_dia_id: int
    ) -> list[DosificacionDetalle]:
        """Trae todo lo ya calculado para ese día, agrupable por almacén en la capa de presentación."""
        stmt = (
            select(DosificacionDetalle)
            .where(DosificacionDetalle.menu_dia_id == menu_dia_id)
            .options(selectinload(DosificacionDetalle.alimento))
            .order_by(DosificacionDetalle.almacen_id, DosificacionDetalle.alimento_id)
        )
        return list((await db.execute(stmt)).scalars().all())


servicio_dosificacion = ServicioDosificacion()
