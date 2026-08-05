"""
Jobs automáticos RN-11/RN-12 (Sesión 20) — llamados por
core/scheduler.py (APScheduler, sin request HTTP) y, en los tests,
directamente con una AsyncSession cruda (ver tests/test_jobs.py).

Cada función asume que el caller hace `await db.commit()` después (mismo
contrato que los endpoints con los repos de crud/*.py: aquí solo se
hace `flush()`).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import current_usuario_id
from app.crud.acta_observacion import acta_observacion_repo
from app.crud.informe_conformidad import informe_conformidad_repo
from app.crud.notificacion import notificacion_repo
from app.crud.parametro_sistema import obtener_entero
from app.models.compras import GuiaRemisionDetalle, OrdenCompra, OrdenCompraDetalle
from app.models.contratos import Contrato
from app.models.inspeccion import ActaObservacion, InspeccionDetalle
from app.models.notificacion import Notificacion


async def _orden_compra_de_inspeccion_detalle(db: AsyncSession, inspeccion_detalle_id: int) -> int | None:
    """Misma cadena InspeccionDetalle -> GuiaRemisionDetalle ->
    OrdenCompraDetalle ya usada en crud/informe_conformidad.py."""
    stmt = (
        select(OrdenCompraDetalle.orden_compra_id)
        .join(
            GuiaRemisionDetalle,
            GuiaRemisionDetalle.orden_compra_detalle_id == OrdenCompraDetalle.orden_compra_detalle_id,
        )
        .join(
            InspeccionDetalle,
            InspeccionDetalle.guia_remision_detalle_id == GuiaRemisionDetalle.guia_remision_detalle_id,
        )
        .where(InspeccionDetalle.inspeccion_detalle_id == inspeccion_detalle_id)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def procesar_actas_vencidas(db: AsyncSession) -> dict:
    """RN-11: actas ABIERTA con plazo_subsanacion vencido se rechazan
    automáticamente; la OC que quede sin ninguna línea OBSERVADO
    pendiente se cierra sola (mismo gate/penalidad automática que el
    cierre manual, crud/informe_conformidad.py::cerrar_orden_compra —
    aquí no se reinventa el cálculo de penalidad, solo se dispara)."""
    stmt = select(ActaObservacion).where(ActaObservacion.estado == "ABIERTA")
    actas = (await db.execute(stmt)).scalars().all()
    vencidas = [acta for acta in actas if acta.plazo_vencido]

    ocs_afectadas: set[int] = set()
    for acta in vencidas:
        current_usuario_id.set(acta.responsable_id)
        try:
            await acta_observacion_repo.vencer_automaticamente(db, acta)
            oc_id = await _orden_compra_de_inspeccion_detalle(db, acta.inspeccion_detalle_id)
            if oc_id is not None:
                ocs_afectadas.add(oc_id)
        finally:
            current_usuario_id.set(None)

    ordenes_cerradas = 0
    for oc_id in ocs_afectadas:
        oc = await db.get(OrdenCompra, oc_id)
        if oc is None:
            continue
        current_usuario_id.set(oc.responsable_id)
        try:
            await informe_conformidad_repo.cerrar_orden_compra(db, oc, responsable_id=oc.responsable_id)
            ordenes_cerradas += 1
        except ValueError:
            # Todavía le queda otra línea OBSERVADO con acta ABIERTA y no
            # vencida — se deja para un día futuro, mismo criterio que el
            # cierre manual (informe_conformidad.py::cerrar_orden_compra).
            pass
        finally:
            current_usuario_id.set(None)

    return {"actas_vencidas": len(vencidas), "ordenes_cerradas": ordenes_cerradas}


async def procesar_alertas_contratos(db: AsyncSession) -> dict:
    """RN-12: alertas de vigencia/saldo de contrato ("Notificación a
    Logística") — sin infraestructura de email en el proyecto, se
    materializan como filas en `notificacion` (Sesión 20), consultables
    vía GET /notificaciones. No se fija current_usuario_id: esta tabla no
    es un "documento" de RN-08 (es un log de alertas, sin FK a usuario en
    su esquema), mismo criterio documentado en core/audit.py para tablas
    de estado sin PK compuesta."""
    umbral_vigencia = await obtener_entero(db, "contratos_dias_alerta_vigencia", default=30)
    umbral_saldo = await obtener_entero(db, "contratos_pct_alerta_saldo", default=15)

    stmt = (
        select(Contrato)
        .where(Contrato.estado == "VIGENTE")
        .options(selectinload(Contrato.productos_contratados))
    )
    contratos = (await db.execute(stmt)).scalars().all()

    notificaciones_creadas = 0
    for contrato in contratos:
        if contrato.calcular_alerta_vigencia(umbral_vigencia):
            if not await notificacion_repo.existe_no_leida(db, "CONTRATO_VIGENCIA", contrato.contrato_id):
                db.add(
                    Notificacion(
                        tipo="CONTRATO_VIGENCIA",
                        referencia_id=contrato.contrato_id,
                        mensaje=(
                            f"El contrato {contrato.numero_contrato} vence en "
                            f"{contrato.dias_para_vencer} días."
                        ),
                    )
                )
                notificaciones_creadas += 1

        for producto_contratado in contrato.productos_contratados:
            if producto_contratado.calcular_alerta_saldo(umbral_saldo):
                if not await notificacion_repo.existe_no_leida(
                    db, "CONTRATO_SALDO", producto_contratado.producto_contratado_id
                ):
                    db.add(
                        Notificacion(
                            tipo="CONTRATO_SALDO",
                            referencia_id=producto_contratado.producto_contratado_id,
                            mensaje=(
                                f"Saldo bajo en el contrato {contrato.numero_contrato} "
                                f"(producto contratado #{producto_contratado.producto_contratado_id})."
                            ),
                        )
                    )
                    notificaciones_creadas += 1

    await db.flush()
    return {"notificaciones_creadas": notificaciones_creadas}
