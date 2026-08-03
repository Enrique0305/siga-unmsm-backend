from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.crud.stock import ajustar_comprometido, obtener_o_crear_stock
from app.models.catalogos import Producto
from app.models.cocina import SolicitudCocina, SolicitudCocinaDetalle
from app.models.dosificacion import DosificacionDetalle
from app.models.organizacion import CentroConsumo
from app.models.planificacion import MenuDia
from app.schemas.cocina import SolicitudCocinaCreate

EPS = 1e-6

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "PENDIENTE": {"ANULADA"},
    "DESPACHADA": set(),
    "ANULADA": set(),
}


class CRUDSolicitudCocina(CRUDBase[SolicitudCocina]):
    async def get_con_detalle(self, db: AsyncSession, solicitud_cocina_id: int) -> SolicitudCocina | None:
        stmt = (
            select(SolicitudCocina)
            .where(SolicitudCocina.solicitud_cocina_id == solicitud_cocina_id)
            .options(selectinload(SolicitudCocina.detalle).selectinload(SolicitudCocinaDetalle.producto))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        almacen_id: int | None = None,
        centro_consumo_id: int | None = None,
        estado: str | None = None,
    ) -> tuple[list[SolicitudCocina], int]:
        stmt = select(SolicitudCocina)
        if almacen_id is not None:
            stmt = stmt.where(SolicitudCocina.almacen_id == almacen_id)
        if centro_consumo_id is not None:
            stmt = stmt.where(SolicitudCocina.centro_consumo_id == centro_consumo_id)
        if estado is not None:
            stmt = stmt.where(SolicitudCocina.estado == estado)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(SolicitudCocina.solicitud_cocina_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(SolicitudCocina.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def _cantidad_teorica_bom(
        self, db: AsyncSession, menu_dia_id: int, centro_consumo_id: int, almacen_id: int, producto_id: int
    ) -> float | None:
        producto = await db.get(Producto, producto_id)
        if producto is None or producto.alimento_id is None:
            return None
        stmt = select(func.sum(DosificacionDetalle.cantidad_bruta_requerida)).where(
            DosificacionDetalle.menu_dia_id == menu_dia_id,
            DosificacionDetalle.centro_consumo_id == centro_consumo_id,
            DosificacionDetalle.almacen_id == almacen_id,
            DosificacionDetalle.alimento_id == producto.alimento_id,
        )
        return (await db.execute(stmt)).scalar_one()

    async def crear(self, db: AsyncSession, data: SolicitudCocinaCreate, solicitado_por_id: int) -> SolicitudCocina:
        centro_consumo = await db.get(CentroConsumo, data.centro_consumo_id)
        if centro_consumo is None:
            raise ValueError("El centro de consumo indicado no existe")
        if await db.get(MenuDia, data.menu_dia_id) is None:
            raise ValueError("El menú del día indicado no existe")

        solicitud = SolicitudCocina(
            numero_solicitud=data.numero_solicitud,
            centro_consumo_id=data.centro_consumo_id,
            almacen_id=centro_consumo.almacen_id,  # RN-17: nunca lo manda el cliente
            menu_dia_id=data.menu_dia_id,
            solicitado_por_id=solicitado_por_id,
        )
        db.add(solicitud)
        await db.flush()

        for linea in data.detalle:
            if await db.get(Producto, linea.producto_id) is None:
                raise ValueError(f"El producto #{linea.producto_id} no existe")

            stock = await obtener_o_crear_stock(db, solicitud.almacen_id, linea.producto_id)
            disponible = stock.stock_fisico - stock.stock_comprometido
            if linea.cantidad_solicitada - disponible > EPS:
                raise ValueError(
                    f"RN-07: la cantidad solicitada ({linea.cantidad_solicitada}) excede el stock "
                    f"disponible ({disponible}) del producto #{linea.producto_id} en este almacén"
                )

            cantidad_teorica = await self._cantidad_teorica_bom(
                db, data.menu_dia_id, data.centro_consumo_id, solicitud.almacen_id, linea.producto_id
            )
            db.add(
                SolicitudCocinaDetalle(
                    solicitud_cocina_id=solicitud.solicitud_cocina_id,
                    producto_id=linea.producto_id,
                    cantidad_solicitada=linea.cantidad_solicitada,
                    cantidad_teorica_bom=cantidad_teorica,
                )
            )
            await ajustar_comprometido(db, solicitud.almacen_id, linea.producto_id, linea.cantidad_solicitada)

        await db.flush()
        return solicitud

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    async def anular(self, db: AsyncSession, solicitud: SolicitudCocina) -> None:
        self.validar_transicion(solicitud.estado, "ANULADA")
        for detalle in solicitud.detalle:
            await ajustar_comprometido(db, solicitud.almacen_id, detalle.producto_id, -detalle.cantidad_solicitada)
        solicitud.estado = "ANULADA"


solicitud_cocina_repo = CRUDSolicitudCocina(SolicitudCocina)
