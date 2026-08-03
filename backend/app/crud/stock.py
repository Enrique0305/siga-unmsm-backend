from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventario import BinCardMovimiento, KardexMovimiento, StockAlmacenProducto

EPS = 1e-6


async def obtener_o_crear_stock(db: AsyncSession, almacen_id: int, producto_id: int) -> StockAlmacenProducto:
    stock = await db.get(StockAlmacenProducto, (almacen_id, producto_id))
    if stock is None:
        stock = StockAlmacenProducto(
            almacen_id=almacen_id, producto_id=producto_id, stock_fisico=0, stock_comprometido=0, valor_promedio_unitario=0
        )
        db.add(stock)
        await db.flush()
    return stock


async def registrar_movimiento(
    db: AsyncSession,
    almacen_id: int,
    producto_id: int,
    tipo_movimiento: str,
    referencia_tipo: str,
    referencia_id: int,
    cantidad: float,
    registrado_por_id: int,
    costo_unitario_entrante: float | None = None,
) -> KardexMovimiento:
    """Único punto de escritura de stock/kardex del módulo Almacén (RN-06:
    kardex_movimiento es insert-only). `cantidad` positivo incrementa,
    negativo decrementa. `costo_unitario_entrante` solo se usa cuando
    cantidad > 0 y hay costo nuevo conocido (ingreso desde OC); si se omite
    (ajuste positivo, devolución desde cocina) o `cantidad < 0` (cualquier
    salida), se usa el `valor_promedio_unitario` vigente — nunca se inventa
    un costo nuevo en una salida."""
    stock = await obtener_o_crear_stock(db, almacen_id, producto_id)

    nuevo_stock_fisico = stock.stock_fisico + cantidad
    if nuevo_stock_fisico < -EPS:
        raise ValueError(
            f"El movimiento dejaría stock físico negativo ({nuevo_stock_fisico}) en "
            f"almacén #{almacen_id}, producto #{producto_id}"
        )
    nuevo_stock_fisico = max(nuevo_stock_fisico, 0.0)

    if cantidad > 0 and costo_unitario_entrante is not None and costo_unitario_entrante > 0:
        valor_actual = stock.stock_fisico * stock.valor_promedio_unitario
        valor_entrante = cantidad * costo_unitario_entrante
        stock.valor_promedio_unitario = (
            (valor_actual + valor_entrante) / nuevo_stock_fisico if nuevo_stock_fisico > 0 else costo_unitario_entrante
        )
        costo_kardex = costo_unitario_entrante
    else:
        costo_kardex = stock.valor_promedio_unitario

    stock.stock_fisico = nuevo_stock_fisico

    kardex = KardexMovimiento(
        almacen_id=almacen_id,
        producto_id=producto_id,
        tipo_movimiento=tipo_movimiento,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        cantidad=cantidad,
        costo_unitario=costo_kardex,
        saldo_cantidad_resultante=nuevo_stock_fisico,
        saldo_valorizado_resultante=nuevo_stock_fisico * stock.valor_promedio_unitario,
        registrado_por_id=registrado_por_id,
    )
    db.add(kardex)
    await db.flush()
    return kardex


async def registrar_bin_card(
    db: AsyncSession,
    almacen_id: int,
    producto_id: int,
    ubicacion_id: int,
    tipo_movimiento: str,
    referencia_tipo: str,
    referencia_id: int,
    cantidad: float,
) -> BinCardMovimiento:
    """Saldo corrido por (almacén, producto, ubicación) — solo se llama al
    ingresar (única tabla de este módulo con columna de ubicación)."""
    stmt = (
        select(BinCardMovimiento)
        .where(
            BinCardMovimiento.almacen_id == almacen_id,
            BinCardMovimiento.producto_id == producto_id,
            BinCardMovimiento.ubicacion_id == ubicacion_id,
        )
        .order_by(BinCardMovimiento.bin_card_id.desc())
        .limit(1)
    )
    ultimo = (await db.execute(stmt)).scalar_one_or_none()
    saldo_anterior = ultimo.saldo_fisico_resultante if ultimo is not None else 0.0

    bin_card = BinCardMovimiento(
        almacen_id=almacen_id,
        producto_id=producto_id,
        ubicacion_id=ubicacion_id,
        tipo_movimiento=tipo_movimiento,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        cantidad=cantidad,
        saldo_fisico_resultante=saldo_anterior + cantidad,
    )
    db.add(bin_card)
    await db.flush()
    return bin_card


async def list_stock(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    producto_id: int | None = None,
) -> tuple[list[StockAlmacenProducto], int]:
    stmt = select(StockAlmacenProducto)
    if almacen_id is not None:
        stmt = stmt.where(StockAlmacenProducto.almacen_id == almacen_id)
    if producto_id is not None:
        stmt = stmt.where(StockAlmacenProducto.producto_id == producto_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        stmt.order_by(StockAlmacenProducto.almacen_id, StockAlmacenProducto.producto_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total


async def list_kardex(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    almacen_id: int | None = None,
    producto_id: int | None = None,
    tipo_movimiento: str | None = None,
) -> tuple[list[KardexMovimiento], int]:
    stmt = select(KardexMovimiento)
    if almacen_id is not None:
        stmt = stmt.where(KardexMovimiento.almacen_id == almacen_id)
    if producto_id is not None:
        stmt = stmt.where(KardexMovimiento.producto_id == producto_id)
    if tipo_movimiento is not None:
        stmt = stmt.where(KardexMovimiento.tipo_movimiento == tipo_movimiento)

    count_stmt = select(func.count()).select_from(stmt.with_only_columns(KardexMovimiento.kardex_id).subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(KardexMovimiento.creado_en.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(stmt)).scalars().all()
    return list(items), total
