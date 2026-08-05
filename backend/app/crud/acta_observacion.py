from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.compras import GuiaRemision, GuiaRemisionDetalle
from app.models.inspeccion import ActaObservacion, Inspeccion, InspeccionDetalle, Subsanacion
from app.schemas.inspeccion import ActaObservacionCreate, SubsanacionCreate

RESULTADOS_REINSPECCION_VALIDOS = ("CONFORME", "NO_CONFORME")


class CRUDActaObservacion(CRUDBase[ActaObservacion]):
    async def get_con_detalle(self, db: AsyncSession, acta_observacion_id: int) -> ActaObservacion | None:
        stmt = (
            select(ActaObservacion)
            .where(ActaObservacion.acta_observacion_id == acta_observacion_id)
            .options(selectinload(ActaObservacion.subsanaciones))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        estado: str | None = None,
        almacen_ids: list[int] | None = None,
    ) -> tuple[list[ActaObservacion], int]:
        stmt = select(ActaObservacion)
        if estado is not None:
            stmt = stmt.where(ActaObservacion.estado == estado)
        if almacen_ids is not None:
            # RN-20 en lecturas: cadena ActaObservacion -> InspeccionDetalle ->
            # GuiaRemisionDetalle -> GuiaRemision.almacen_destino_id (Sesión 15).
            stmt = (
                stmt.join(InspeccionDetalle, ActaObservacion.inspeccion_detalle_id == InspeccionDetalle.inspeccion_detalle_id)
                .join(GuiaRemisionDetalle, InspeccionDetalle.guia_remision_detalle_id == GuiaRemisionDetalle.guia_remision_detalle_id)
                .join(GuiaRemision, GuiaRemisionDetalle.guia_remision_id == GuiaRemision.guia_remision_id)
                .where(GuiaRemision.almacen_destino_id.in_(almacen_ids))
            )

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(ActaObservacion.acta_observacion_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(ActaObservacion.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear_acta(
        self, db: AsyncSession, inspeccion_detalle_id: int, data: ActaObservacionCreate, responsable_id: int
    ) -> ActaObservacion:
        stmt = (
            select(InspeccionDetalle)
            .where(InspeccionDetalle.inspeccion_detalle_id == inspeccion_detalle_id)
            .options(selectinload(InspeccionDetalle.acta_observacion))
        )
        detalle = (await db.execute(stmt)).scalar_one_or_none()
        if detalle is None:
            raise ValueError("La línea de inspección indicada no existe")
        if detalle.resultado != "OBSERVADO":
            raise ValueError("Solo se puede levantar un acta sobre una línea con resultado OBSERVADO")
        if detalle.acta_observacion is not None:
            raise ValueError("Esta línea de inspección ya tiene un acta de observación registrada")

        acta = ActaObservacion(
            numero_acta=data.numero_acta,
            inspeccion_detalle_id=inspeccion_detalle_id,
            motivo=data.motivo,
            cantidad_observada=detalle.cantidad_observada,
            responsable_id=responsable_id,
            plazo_subsanacion=data.plazo_subsanacion,
        )
        db.add(acta)
        await db.flush()
        return acta

    async def crear_subsanacion(
        self, db: AsyncSession, acta_observacion_id: int, data: SubsanacionCreate
    ) -> Subsanacion:
        acta = await db.get(ActaObservacion, acta_observacion_id)
        if acta is None:
            raise ValueError("El acta de observación indicada no existe")
        if acta.estado != "ABIERTA":
            raise ValueError(f"El acta #{acta.numero_acta} ya no está ABIERTA (estado actual: {acta.estado})")

        subsanacion = Subsanacion(
            acta_observacion_id=acta_observacion_id,
            fecha_presentacion=data.fecha_presentacion,
            descripcion=data.descripcion,
        )
        db.add(subsanacion)
        await db.flush()
        return subsanacion

    async def _quedan_actas_abiertas(self, db: AsyncSession, guia_remision_id: int) -> bool:
        stmt = (
            select(func.count())
            .select_from(ActaObservacion)
            .join(InspeccionDetalle, ActaObservacion.inspeccion_detalle_id == InspeccionDetalle.inspeccion_detalle_id)
            .join(Inspeccion, InspeccionDetalle.inspeccion_id == Inspeccion.inspeccion_id)
            .where(Inspeccion.guia_remision_id == guia_remision_id, ActaObservacion.estado == "ABIERTA")
        )
        return (await db.execute(stmt)).scalar_one() > 0

    async def registrar_reinspeccion(
        self, db: AsyncSession, subsanacion_id: int, resultado_reinspeccion: str, inspector_id: int
    ) -> Subsanacion:
        if resultado_reinspeccion not in RESULTADOS_REINSPECCION_VALIDOS:
            raise ValueError("resultado_reinspeccion debe ser CONFORME o NO_CONFORME")

        stmt = (
            select(Subsanacion)
            .where(Subsanacion.subsanacion_id == subsanacion_id)
            .options(selectinload(Subsanacion.acta_observacion))
        )
        subsanacion = (await db.execute(stmt)).scalar_one_or_none()
        if subsanacion is None:
            raise ValueError("La subsanación indicada no existe")
        if subsanacion.resultado_reinspeccion is not None:
            raise ValueError("Esta subsanación ya tiene un resultado de re-inspección registrado")

        acta = subsanacion.acta_observacion
        if acta.estado != "ABIERTA":
            raise ValueError(f"El acta #{acta.numero_acta} ya no está ABIERTA (estado actual: {acta.estado})")

        subsanacion.resultado_reinspeccion = resultado_reinspeccion
        subsanacion.inspector_id = inspector_id
        # RECHAZADA es terminal en este módulo (un solo intento); reintentos
        # ilimitados quedarían para una decisión de producto posterior.
        acta.estado = "SUBSANADA" if resultado_reinspeccion == "CONFORME" else "RECHAZADA"
        await db.flush()

        stmt_guia = (
            select(Inspeccion.guia_remision_id)
            .join(InspeccionDetalle, Inspeccion.inspeccion_id == InspeccionDetalle.inspeccion_id)
            .where(InspeccionDetalle.inspeccion_detalle_id == acta.inspeccion_detalle_id)
        )
        guia_remision_id = (await db.execute(stmt_guia)).scalar_one()

        # RN de este módulo: la guía avanza a SUBSANADO cuando ya no le queda
        # ninguna acta ABIERTA. CERRADO/PENALIZADO (RN-11) los decide Módulo 5.
        if not await self._quedan_actas_abiertas(db, guia_remision_id):
            guia = await db.get(GuiaRemision, guia_remision_id)
            if guia.estado == "OBSERVADO":
                guia.estado = "SUBSANADO"

        return subsanacion


acta_observacion_repo = CRUDActaObservacion(ActaObservacion)
