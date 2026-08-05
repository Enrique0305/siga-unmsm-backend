from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.compras import OrdenCompra, PedidoSemanal
from app.models.contratos import Contrato
from app.models.organizacion import Almacen
from app.models.planificacion import MenuQuincenal
from app.schemas.compra import PedidoSemanalCreate


class CRUDPedidoSemanal(CRUDBase[PedidoSemanal]):
    async def get_con_relaciones(self, db: AsyncSession, pedido_semanal_id: int) -> PedidoSemanal | None:
        stmt = (
            select(PedidoSemanal)
            .where(PedidoSemanal.pedido_semanal_id == pedido_semanal_id)
            .options(selectinload(PedidoSemanal.almacen))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        orden_compra_id: int | None = None,
        almacen_id: int | None = None,
        almacen_ids: list[int] | None = None,
        menu_id: int | None = None,
        proveedor_id: int | None = None,
    ) -> tuple[list[PedidoSemanal], int]:
        stmt = select(PedidoSemanal).options(selectinload(PedidoSemanal.almacen))
        if orden_compra_id is not None:
            stmt = stmt.where(PedidoSemanal.orden_compra_id == orden_compra_id)
        if almacen_id is not None:
            stmt = stmt.where(PedidoSemanal.almacen_id == almacen_id)
        if almacen_ids is not None:
            stmt = stmt.where(PedidoSemanal.almacen_id.in_(almacen_ids))
        if proveedor_id is not None:
            stmt = stmt.join(OrdenCompra, PedidoSemanal.orden_compra_id == OrdenCompra.orden_compra_id).join(
                Contrato, OrdenCompra.contrato_id == Contrato.contrato_id
            ).where(Contrato.proveedor_id == proveedor_id)
        if menu_id is not None:
            stmt = stmt.where(PedidoSemanal.menu_id == menu_id)

        count_stmt = select(func.count()).select_from(
            stmt.with_only_columns(PedidoSemanal.pedido_semanal_id).subquery()
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(PedidoSemanal.semana_inicio.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear(self, db: AsyncSession, data: PedidoSemanalCreate) -> PedidoSemanal:
        if await db.get(OrdenCompra, data.orden_compra_id) is None:
            raise ValueError("La orden de compra indicada no existe")
        if await db.get(MenuQuincenal, data.menu_id) is None:
            raise ValueError("El menú quincenal indicado no existe")
        if await db.get(Almacen, data.almacen_id) is None:
            raise ValueError("El almacén indicado no existe")

        pedido = PedidoSemanal(**data.model_dump())
        db.add(pedido)
        await db.flush()
        await db.refresh(pedido, attribute_names=["almacen"])
        return pedido


pedido_semanal_repo = CRUDPedidoSemanal(PedidoSemanal)
