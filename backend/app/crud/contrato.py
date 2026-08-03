from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.contratos import Contrato, CronogramaEntrega, ProductoContratado, Proveedor
from app.models.planificacion import RequerimientoAnual
from app.schemas.contrato import ContratoCreate, CronogramaEntregaIn, ProductoContratadoIn

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "VIGENTE": {"SUSPENDIDO", "CERRADO"},
    "SUSPENDIDO": {"VIGENTE", "CERRADO"},
    "CERRADO": set(),
}

# Estados de requerimiento_anual que habilitan crear contratos sobre él
# (sección 4.1 del diseño: "el requerimiento anual aprobado es el techo
# contra el cual se validarán todos los contratos posteriores").
ESTADOS_REQUERIMIENTO_HABILITADOS = {"APROBADO", "VIGENTE"}


class CRUDContrato(CRUDBase[Contrato]):
    async def get_con_detalle(self, db: AsyncSession, contrato_id: int) -> Contrato | None:
        stmt = (
            select(Contrato)
            .where(Contrato.contrato_id == contrato_id)
            .options(
                selectinload(Contrato.cronograma),
                selectinload(Contrato.productos_contratados).selectinload(ProductoContratado.producto),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        proveedor_id: int | None = None,
        estado: str | None = None,
        buscar: str | None = None,
    ) -> tuple[list[Contrato], int]:
        stmt = select(Contrato)
        if proveedor_id is not None:
            stmt = stmt.where(Contrato.proveedor_id == proveedor_id)
        if estado is not None:
            stmt = stmt.where(Contrato.estado == estado)
        if buscar:
            stmt = stmt.where(Contrato.numero_contrato.ilike(f"%{buscar}%"))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Contrato.contrato_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Contrato.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear(self, db: AsyncSession, data: ContratoCreate, responsable_id: int) -> Contrato:
        requerimiento = await db.get(RequerimientoAnual, data.requerimiento_anual_id)
        if requerimiento is None:
            raise ValueError("El requerimiento anual indicado no existe")
        if requerimiento.estado not in ESTADOS_REQUERIMIENTO_HABILITADOS:
            raise ValueError(
                "El requerimiento anual debe estar APROBADO o VIGENTE antes de contratar sobre él"
            )

        proveedor = await db.get(Proveedor, data.proveedor_id)
        if proveedor is None:
            raise ValueError("El proveedor indicado no existe")

        contrato = Contrato(
            numero_contrato=data.numero_contrato,
            proveedor_id=data.proveedor_id,
            requerimiento_anual_id=data.requerimiento_anual_id,
            fecha_inicio=data.fecha_inicio,
            fecha_fin=data.fecha_fin,
            presupuesto_total=data.presupuesto_total,
            condiciones=data.condiciones,
            penalidad_json=data.penalidad_json,
            responsable_id=responsable_id,
        )
        db.add(contrato)
        await db.flush()

        for linea in data.cronograma:
            db.add(CronogramaEntrega(contrato_id=contrato.contrato_id, **linea.model_dump()))
        await db.flush()
        return contrato

    async def agregar_cronograma(
        self, db: AsyncSession, contrato_id: int, data: CronogramaEntregaIn
    ) -> CronogramaEntrega:
        entrega = CronogramaEntrega(contrato_id=contrato_id, **data.model_dump())
        db.add(entrega)
        await db.flush()
        return entrega

    async def agregar_producto_contratado(
        self, db: AsyncSession, contrato_id: int, data: ProductoContratadoIn
    ) -> ProductoContratado:
        """Inicializa saldo_fisico = cantidad_contratada y saldo_monetario = tope
        monetario (precio × cantidad). El descuento de saldo al emitir Órdenes de
        Compra (RN-01/RN-19) pertenece al Módulo 3."""
        producto_contratado = ProductoContratado(
            contrato_id=contrato_id,
            producto_id=data.producto_id,
            precio_unitario=data.precio_unitario,
            cantidad_contratada=data.cantidad_contratada,
            saldo_fisico=data.cantidad_contratada,
            saldo_monetario=data.precio_unitario * data.cantidad_contratada,
        )
        db.add(producto_contratado)
        await db.flush()
        # tope_monetario es GENERATED ALWAYS en MySQL (ver models/contratos.py) y
        # queda "expirado" tras el INSERT; refresh() lo recarga junto con la
        # relación producto (lazy="joined") en la misma sentencia SELECT, evitando
        # I/O implícito en un acceso posterior dentro de la sesión async.
        await db.refresh(producto_contratado)
        return producto_contratado

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")


contrato_repo = CRUDContrato(Contrato)
