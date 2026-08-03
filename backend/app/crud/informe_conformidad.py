from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.crud.orden_compra import orden_compra_repo
from app.models.compras import GuiaRemisionDetalle, OrdenCompra, OrdenCompraDetalle
from app.models.contratos import ProductoContratado
from app.models.inspeccion import ActaObservacion, InspeccionDetalle
from app.models.pagos import InformeConformidadDetalle, InformeConformidadPago, Penalidad
from app.schemas.pagos import InformeConformidadPagoCreate

TRANSICIONES_VALIDAS_INFORME: dict[str, set[str]] = {
    "ENVIADO": {"RECIBIDO", "DEVUELTO"},
    "RECIBIDO": {"EN_PROCESO_DE_PAGO", "DEVUELTO"},
    "EN_PROCESO_DE_PAGO": {"PAGADO", "DEVUELTO"},
    "PAGADO": set(),
    "DEVUELTO": set(),
}


async def _inspecciones_de_linea(db: AsyncSession, orden_compra_detalle_id: int) -> list[InspeccionDetalle]:
    """Recorre orden_compra_detalle -> guia_remision_detalle -> inspeccion_detalle
    (con su acta_observacion, si tiene) — misma cadena de denormalización ya
    usada en Inspección/Almacén."""
    stmt = (
        select(InspeccionDetalle)
        .join(
            GuiaRemisionDetalle,
            InspeccionDetalle.guia_remision_detalle_id == GuiaRemisionDetalle.guia_remision_detalle_id,
        )
        .where(GuiaRemisionDetalle.orden_compra_detalle_id == orden_compra_detalle_id)
        .options(selectinload(InspeccionDetalle.acta_observacion))
    )
    return list((await db.execute(stmt)).scalars().all())


def _sumar_conformidad(inspecciones: list[InspeccionDetalle]) -> tuple[float, float]:
    """RN-05: observado no entra a la Conformidad de Pago hasta que su acta
    quede SUBSANADA (entonces sí se paga) o RECHAZADA (se retiene)."""
    conforme = 0.0
    retenida = 0.0
    for insp in inspecciones:
        conforme += insp.cantidad_conforme
        if insp.resultado == "OBSERVADO" and insp.acta_observacion is not None:
            if insp.acta_observacion.estado == "SUBSANADA":
                conforme += insp.cantidad_observada
            elif insp.acta_observacion.estado == "RECHAZADA":
                retenida += insp.cantidad_observada
    return conforme, retenida


async def _hay_observaciones_sin_resolver(db: AsyncSession, orden_compra_id: int) -> bool:
    stmt = (
        select(func.count())
        .select_from(InspeccionDetalle)
        .join(
            GuiaRemisionDetalle,
            InspeccionDetalle.guia_remision_detalle_id == GuiaRemisionDetalle.guia_remision_detalle_id,
        )
        .join(
            OrdenCompraDetalle,
            GuiaRemisionDetalle.orden_compra_detalle_id == OrdenCompraDetalle.orden_compra_detalle_id,
        )
        .outerjoin(ActaObservacion, ActaObservacion.inspeccion_detalle_id == InspeccionDetalle.inspeccion_detalle_id)
        .where(
            OrdenCompraDetalle.orden_compra_id == orden_compra_id,
            InspeccionDetalle.resultado == "OBSERVADO",
            (ActaObservacion.acta_observacion_id.is_(None)) | (ActaObservacion.estado == "ABIERTA"),
        )
    )
    return (await db.execute(stmt)).scalar_one() > 0


class CRUDInformeConformidad(CRUDBase[InformeConformidadPago]):
    async def get_con_detalle(self, db: AsyncSession, informe_id: int) -> InformeConformidadPago | None:
        stmt = (
            select(InformeConformidadPago)
            .where(InformeConformidadPago.informe_id == informe_id)
            .options(
                selectinload(InformeConformidadPago.detalle)
                .selectinload(InformeConformidadDetalle.orden_compra_detalle)
                .selectinload(OrdenCompraDetalle.producto_contratado)
                .selectinload(ProductoContratado.producto)
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self, db: AsyncSession, page: int = 1, page_size: int = 20, orden_compra_id: int | None = None, estado: str | None = None
    ) -> tuple[list[InformeConformidadPago], int]:
        stmt = select(InformeConformidadPago)
        if orden_compra_id is not None:
            stmt = stmt.where(InformeConformidadPago.orden_compra_id == orden_compra_id)
        if estado is not None:
            stmt = stmt.where(InformeConformidadPago.estado == estado)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(InformeConformidadPago.informe_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(InformeConformidadPago.fecha_envio.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def cerrar_orden_compra(self, db: AsyncSession, orden_compra: OrdenCompra, responsable_id: int) -> OrdenCompra:
        """Gate: ninguna línea OBSERVADO puede quedar sin una acta resuelta
        (ni ABIERTA ni sin acta). Crea una Penalidad automática por cada acta
        RECHAZADA aún no penalizada; la OC cierra PENALIZADO si se generó
        alguna (nueva o preexistente), si no CERRADO."""
        orden_compra_repo.validar_transicion(orden_compra.estado, "CERRADO")

        if await _hay_observaciones_sin_resolver(db, orden_compra.orden_compra_id):
            raise ValueError(
                "No se puede cerrar la OC: tiene líneas OBSERVADO sin acta de observación resuelta"
            )

        stmt = select(OrdenCompraDetalle).where(OrdenCompraDetalle.orden_compra_id == orden_compra.orden_compra_id)
        detalles = (await db.execute(stmt)).scalars().all()

        stmt_penal = select(Penalidad.acta_observacion_id).where(
            Penalidad.orden_compra_id == orden_compra.orden_compra_id
        )
        actas_ya_penalizadas = set((await db.execute(stmt_penal)).scalars().all())
        hay_penalidad = len(actas_ya_penalizadas) > 0

        for detalle in detalles:
            inspecciones = await _inspecciones_de_linea(db, detalle.orden_compra_detalle_id)
            for insp in inspecciones:
                acta = insp.acta_observacion
                if insp.resultado != "OBSERVADO" or acta is None or acta.estado != "RECHAZADA":
                    continue
                if acta.acta_observacion_id in actas_ya_penalizadas:
                    continue

                db.add(
                    Penalidad(
                        orden_compra_id=orden_compra.orden_compra_id,
                        acta_observacion_id=acta.acta_observacion_id,
                        monto_penalidad=insp.cantidad_observada * detalle.precio_unitario_aplicado,
                        motivo=f"Observación rechazada — acta {acta.numero_acta}",
                    )
                )
                actas_ya_penalizadas.add(acta.acta_observacion_id)
                hay_penalidad = True

        orden_compra.estado = "PENALIZADO" if hay_penalidad else "CERRADO"
        await db.flush()
        return orden_compra

    async def generar_informe(
        self, db: AsyncSession, data: InformeConformidadPagoCreate, generado_por_id: int
    ) -> InformeConformidadPago:
        orden_compra = await db.get(OrdenCompra, data.orden_compra_id)
        if orden_compra is None:
            raise ValueError("La orden de compra indicada no existe")
        if orden_compra.estado not in ("CERRADO", "PENALIZADO"):
            raise ValueError("La OC debe estar CERRADO o PENALIZADO para generar el informe de conformidad")

        stmt_existente = select(InformeConformidadPago.informe_id).where(
            InformeConformidadPago.orden_compra_id == data.orden_compra_id
        )
        if (await db.execute(stmt_existente)).scalar_one_or_none() is not None:
            raise ValueError("Ya existe un informe de conformidad para esta orden de compra")

        stmt = select(OrdenCompraDetalle).where(OrdenCompraDetalle.orden_compra_id == data.orden_compra_id)
        detalles = (await db.execute(stmt)).scalars().all()

        stmt_penal = select(func.sum(Penalidad.monto_penalidad)).where(
            Penalidad.orden_compra_id == data.orden_compra_id
        )
        monto_penalidad_total = (await db.execute(stmt_penal)).scalar_one() or 0.0

        informe = InformeConformidadPago(
            numero_informe=data.numero_informe,
            orden_compra_id=data.orden_compra_id,
            monto_conforme_total=0,
            monto_retenido_total=0,
            monto_penalidad_total=monto_penalidad_total,
            generado_por_id=generado_por_id,
        )
        db.add(informe)
        await db.flush()

        monto_conforme_total = 0.0
        monto_retenido_total = 0.0
        for detalle in detalles:
            inspecciones = await _inspecciones_de_linea(db, detalle.orden_compra_detalle_id)
            conforme, retenida = _sumar_conformidad(inspecciones)
            monto_conforme = conforme * detalle.precio_unitario_aplicado
            monto_retenido = retenida * detalle.precio_unitario_aplicado

            db.add(
                InformeConformidadDetalle(
                    informe_id=informe.informe_id,
                    orden_compra_detalle_id=detalle.orden_compra_detalle_id,
                    cantidad_conforme=conforme,
                    monto_conforme=monto_conforme,
                    cantidad_retenida=retenida,
                    monto_retenido=monto_retenido,
                )
            )
            monto_conforme_total += monto_conforme
            monto_retenido_total += monto_retenido

        informe.monto_conforme_total = monto_conforme_total
        informe.monto_retenido_total = monto_retenido_total
        await db.flush()
        return informe

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS_INFORME.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    async def cambiar_estado(self, db: AsyncSession, informe: InformeConformidadPago, estado_nuevo: str) -> InformeConformidadPago:
        self.validar_transicion(informe.estado, estado_nuevo)
        informe.estado = estado_nuevo
        if estado_nuevo == "PAGADO":
            informe.fecha_pago = datetime.now(timezone.utc)
        await db.flush()
        return informe


informe_conformidad_repo = CRUDInformeConformidad(InformeConformidadPago)
