from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.crud.stock import registrar_movimiento
from app.models.inventario import KardexMovimiento, TransferenciaAlmacen, TransferenciaAlmacenDetalle
from app.models.organizacion import Almacen
from app.schemas.inventario import TransferenciaAlmacenCreate, TransferenciaRecepcionIn

EPS = 1e-6


class CRUDTransferenciaAlmacen(CRUDBase[TransferenciaAlmacen]):
    async def get_con_detalle(self, db: AsyncSession, transferencia_id: int) -> TransferenciaAlmacen | None:
        stmt = (
            select(TransferenciaAlmacen)
            .where(TransferenciaAlmacen.transferencia_id == transferencia_id)
            .options(selectinload(TransferenciaAlmacen.detalle).selectinload(TransferenciaAlmacenDetalle.producto))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        almacen_origen_id: int | None = None,
        almacen_destino_id: int | None = None,
        almacen_ids: list[int] | None = None,
        estado: str | None = None,
    ) -> tuple[list[TransferenciaAlmacen], int]:
        stmt = select(TransferenciaAlmacen)
        if almacen_origen_id is not None:
            stmt = stmt.where(TransferenciaAlmacen.almacen_origen_id == almacen_origen_id)
        if almacen_destino_id is not None:
            stmt = stmt.where(TransferenciaAlmacen.almacen_destino_id == almacen_destino_id)
        if almacen_ids is not None:
            # RN-20 en lecturas: visible si el usuario tiene acceso a origen O destino.
            stmt = stmt.where(
                or_(
                    TransferenciaAlmacen.almacen_origen_id.in_(almacen_ids),
                    TransferenciaAlmacen.almacen_destino_id.in_(almacen_ids),
                )
            )
        if estado is not None:
            stmt = stmt.where(TransferenciaAlmacen.estado == estado)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(TransferenciaAlmacen.transferencia_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(TransferenciaAlmacen.fecha_salida.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear(
        self, db: AsyncSession, data: TransferenciaAlmacenCreate, responsable_origen_id: int
    ) -> TransferenciaAlmacen:
        if data.almacen_origen_id == data.almacen_destino_id:
            raise ValueError("El almacén de origen y destino no pueden ser el mismo")
        if await db.get(Almacen, data.almacen_origen_id) is None:
            raise ValueError("El almacén de origen no existe")
        if await db.get(Almacen, data.almacen_destino_id) is None:
            raise ValueError("El almacén de destino no existe")

        transferencia = TransferenciaAlmacen(
            numero_transferencia=data.numero_transferencia,
            almacen_origen_id=data.almacen_origen_id,
            almacen_destino_id=data.almacen_destino_id,
            responsable_origen_id=responsable_origen_id,
        )
        db.add(transferencia)
        await db.flush()

        for linea in data.detalle:
            db.add(
                TransferenciaAlmacenDetalle(
                    transferencia_id=transferencia.transferencia_id,
                    producto_id=linea.producto_id,
                    cantidad_enviada=linea.cantidad_enviada,
                )
            )
            # RN-18: la salida se descuenta de inmediato; el ingreso al destino
            # solo ocurre al confirmar la recepción (registrar_recepcion).
            await registrar_movimiento(
                db,
                almacen_id=data.almacen_origen_id,
                producto_id=linea.producto_id,
                tipo_movimiento="TRANSFERENCIA_SALIDA",
                referencia_tipo="transferencia_almacen",
                referencia_id=transferencia.transferencia_id,
                cantidad=-linea.cantidad_enviada,
                registrado_por_id=responsable_origen_id,
            )

        await db.flush()
        return transferencia

    async def _costo_salida(
        self, db: AsyncSession, transferencia_id: int, almacen_origen_id: int, producto_id: int
    ) -> float:
        """Reusa el costo_unitario registrado en el kardex de la salida
        original para preservar la valorización al ingresar en destino."""
        stmt = (
            select(KardexMovimiento.costo_unitario)
            .where(
                KardexMovimiento.referencia_tipo == "transferencia_almacen",
                KardexMovimiento.referencia_id == transferencia_id,
                KardexMovimiento.almacen_id == almacen_origen_id,
                KardexMovimiento.producto_id == producto_id,
                KardexMovimiento.tipo_movimiento == "TRANSFERENCIA_SALIDA",
            )
            .order_by(KardexMovimiento.kardex_id.desc())
            .limit(1)
        )
        costo = (await db.execute(stmt)).scalar_one_or_none()
        if costo is None:
            raise ValueError(f"No se encontró el movimiento de salida original del producto #{producto_id}")
        return costo

    async def registrar_recepcion(
        self,
        db: AsyncSession,
        transferencia: TransferenciaAlmacen,
        data: TransferenciaRecepcionIn,
        responsable_destino_id: int,
    ) -> TransferenciaAlmacen:
        if transferencia.estado != "EN_TRANSITO":
            raise ValueError(f"La transferencia ya está {transferencia.estado}")

        ids_payload = {linea.transferencia_detalle_id for linea in data.detalle}
        ids_transferencia = {d.transferencia_detalle_id for d in transferencia.detalle}
        if ids_payload != ids_transferencia:
            raise ValueError(
                "Debe registrarse la recepción de todas las líneas de esta transferencia, y solo de ella"
            )

        detalle_por_id = {d.transferencia_detalle_id: d for d in transferencia.detalle}
        alguna_diferencia = False

        for linea in data.detalle:
            detalle = detalle_por_id[linea.transferencia_detalle_id]
            costo_unitario = await self._costo_salida(
                db, transferencia.transferencia_id, transferencia.almacen_origen_id, detalle.producto_id
            )

            detalle.cantidad_recibida = linea.cantidad_recibida
            detalle.observacion_diferencia = linea.observacion_diferencia
            if abs(linea.cantidad_recibida - detalle.cantidad_enviada) > EPS:
                alguna_diferencia = True

            if linea.cantidad_recibida > EPS:
                await registrar_movimiento(
                    db,
                    almacen_id=transferencia.almacen_destino_id,
                    producto_id=detalle.producto_id,
                    tipo_movimiento="TRANSFERENCIA_INGRESO",
                    referencia_tipo="transferencia_almacen",
                    referencia_id=transferencia.transferencia_id,
                    cantidad=linea.cantidad_recibida,
                    registrado_por_id=responsable_destino_id,
                    costo_unitario_entrante=costo_unitario,
                )

        transferencia.responsable_destino_id = responsable_destino_id
        transferencia.fecha_recepcion = datetime.now(timezone.utc)
        transferencia.estado = "RECIBIDA_CON_DIFERENCIA" if alguna_diferencia else "RECIBIDA_CONFORME"

        await db.flush()
        return transferencia


transferencia_almacen_repo = CRUDTransferenciaAlmacen(TransferenciaAlmacen)
