from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.stock import registrar_movimiento
from app.models.catalogos import Producto
from app.models.inventario import AjusteInventario, Devolucion, Merma
from app.models.organizacion import Almacen
from app.schemas.inventario import AjusteInventarioCreate, DevolucionCreate, MermaCreate

TIPO_MOVIMIENTO_KARDEX = {
    "A_PROVEEDOR": "DEVOLUCION_PROVEEDOR",
    "DESDE_COCINA": "DEVOLUCION_COCINA",
}


async def _validar_almacen_producto(db: AsyncSession, almacen_id: int, producto_id: int) -> None:
    if await db.get(Almacen, almacen_id) is None:
        raise ValueError("El almacén indicado no existe")
    if await db.get(Producto, producto_id) is None:
        raise ValueError("El producto indicado no existe")


async def crear_ajuste(db: AsyncSession, data: AjusteInventarioCreate, responsable_id: int) -> AjusteInventario:
    await _validar_almacen_producto(db, data.almacen_id, data.producto_id)

    ajuste = AjusteInventario(
        almacen_id=data.almacen_id,
        producto_id=data.producto_id,
        cantidad_ajuste=data.cantidad_ajuste,
        motivo=data.motivo,
        responsable_id=responsable_id,
    )
    db.add(ajuste)
    await db.flush()

    await registrar_movimiento(
        db,
        almacen_id=data.almacen_id,
        producto_id=data.producto_id,
        tipo_movimiento="AJUSTE",
        referencia_tipo="ajuste_inventario",
        referencia_id=ajuste.ajuste_id,
        cantidad=data.cantidad_ajuste,
        registrado_por_id=responsable_id,
    )
    return ajuste


async def crear_merma(db: AsyncSession, data: MermaCreate, responsable_id: int) -> Merma:
    await _validar_almacen_producto(db, data.almacen_id, data.producto_id)

    merma = Merma(
        almacen_id=data.almacen_id,
        producto_id=data.producto_id,
        cantidad=data.cantidad,
        motivo=data.motivo,
        responsable_id=responsable_id,
    )
    db.add(merma)
    await db.flush()

    await registrar_movimiento(
        db,
        almacen_id=data.almacen_id,
        producto_id=data.producto_id,
        tipo_movimiento="MERMA",
        referencia_tipo="merma",
        referencia_id=merma.merma_id,
        cantidad=-data.cantidad,
        registrado_por_id=responsable_id,
    )
    return merma


async def crear_devolucion(db: AsyncSession, data: DevolucionCreate, responsable_id: int) -> Devolucion:
    if data.tipo not in TIPO_MOVIMIENTO_KARDEX:
        raise ValueError("tipo debe ser A_PROVEEDOR o DESDE_COCINA")
    await _validar_almacen_producto(db, data.almacen_id, data.producto_id)

    devolucion = Devolucion(
        almacen_id=data.almacen_id,
        producto_id=data.producto_id,
        tipo=data.tipo,
        cantidad=data.cantidad,
        referencia_tipo=data.referencia_tipo,
        referencia_id=data.referencia_id,
        motivo=data.motivo,
        responsable_id=responsable_id,
    )
    db.add(devolucion)
    await db.flush()

    cantidad_kardex = data.cantidad if data.tipo == "DESDE_COCINA" else -data.cantidad
    await registrar_movimiento(
        db,
        almacen_id=data.almacen_id,
        producto_id=data.producto_id,
        tipo_movimiento=TIPO_MOVIMIENTO_KARDEX[data.tipo],
        referencia_tipo="devolucion",
        referencia_id=devolucion.devolucion_id,
        cantidad=cantidad_kardex,
        registrado_por_id=responsable_id,
    )
    return devolucion
