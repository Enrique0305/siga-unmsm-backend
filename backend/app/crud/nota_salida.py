from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.crud.stock import ajustar_comprometido, registrar_movimiento
from app.models.cocina import NotaSalida, NotaSalidaDetalle, SolicitudCocina, SolicitudCocinaDetalle
from app.schemas.cocina import NotaSalidaCreate

EPS = 1e-6


class CRUDNotaSalida(CRUDBase[NotaSalida]):
    async def get_con_detalle(self, db: AsyncSession, nota_salida_id: int) -> NotaSalida | None:
        stmt = (
            select(NotaSalida)
            .where(NotaSalida.nota_salida_id == nota_salida_id)
            .options(
                selectinload(NotaSalida.detalle)
                .selectinload(NotaSalidaDetalle.solicitud_cocina_detalle)
                .selectinload(SolicitudCocinaDetalle.producto)
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        almacen_id: int | None = None,
        solicitud_cocina_id: int | None = None,
    ) -> tuple[list[NotaSalida], int]:
        stmt = select(NotaSalida)
        if almacen_id is not None:
            stmt = stmt.where(NotaSalida.almacen_id == almacen_id)
        if solicitud_cocina_id is not None:
            stmt = stmt.where(NotaSalida.solicitud_cocina_id == solicitud_cocina_id)

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(NotaSalida.nota_salida_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(NotaSalida.fecha_salida.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear(self, db: AsyncSession, data: NotaSalidaCreate, almacenero_id: int) -> NotaSalida:
        stmt = (
            select(SolicitudCocina)
            .where(SolicitudCocina.solicitud_cocina_id == data.solicitud_cocina_id)
            .options(selectinload(SolicitudCocina.detalle).selectinload(SolicitudCocinaDetalle.producto))
        )
        solicitud = (await db.execute(stmt)).scalar_one_or_none()
        if solicitud is None:
            raise ValueError("La solicitud de cocina indicada no existe")
        if solicitud.estado != "PENDIENTE":
            raise ValueError(f"La solicitud ya está {solicitud.estado}")

        ids_payload = {linea.solicitud_cocina_detalle_id for linea in data.detalle}
        ids_solicitud = {d.solicitud_cocina_detalle_id for d in solicitud.detalle}
        if ids_payload != ids_solicitud:
            raise ValueError("La nota de salida debe cubrir todas las líneas de la solicitud, y solo de ella")

        nota = NotaSalida(
            numero_nota=data.numero_nota,
            solicitud_cocina_id=solicitud.solicitud_cocina_id,
            almacen_id=solicitud.almacen_id,  # RN-17: nunca lo manda el cliente
            almacenero_id=almacenero_id,
        )
        db.add(nota)
        await db.flush()

        detalle_por_id = {d.solicitud_cocina_detalle_id: d for d in solicitud.detalle}
        for linea in data.detalle:
            detalle_solicitud = detalle_por_id[linea.solicitud_cocina_detalle_id]
            if linea.cantidad_despachada - detalle_solicitud.cantidad_solicitada > EPS:
                raise ValueError(
                    f"La cantidad despachada ({linea.cantidad_despachada}) no puede superar la solicitada "
                    f"({detalle_solicitud.cantidad_solicitada}) de la línea "
                    f"#{linea.solicitud_cocina_detalle_id}"
                )

            kardex = await registrar_movimiento(
                db,
                almacen_id=solicitud.almacen_id,
                producto_id=detalle_solicitud.producto_id,
                tipo_movimiento="SALIDA",
                referencia_tipo="nota_salida",
                referencia_id=nota.nota_salida_id,
                cantidad=-linea.cantidad_despachada,
                registrado_por_id=almacenero_id,
            )
            # libera toda la reserva de la línea, se haya despachado completo o no
            await ajustar_comprometido(
                db, solicitud.almacen_id, detalle_solicitud.producto_id, -detalle_solicitud.cantidad_solicitada
            )

            db.add(
                NotaSalidaDetalle(
                    nota_salida_id=nota.nota_salida_id,
                    solicitud_cocina_detalle_id=linea.solicitud_cocina_detalle_id,
                    cantidad_despachada=linea.cantidad_despachada,
                    costo_unitario=kardex.costo_unitario,
                )
            )

        solicitud.estado = "DESPACHADA"
        await db.flush()
        return nota


nota_salida_repo = CRUDNotaSalida(NotaSalida)
