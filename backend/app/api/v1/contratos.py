from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_proveedor
from app.crud.contrato import contrato_repo
from app.crud.parametro_sistema import obtener_entero
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.contrato import (
    ContratoCreate,
    ContratoDetailOut,
    ContratoEstadoUpdate,
    ContratoListOut,
    ContratoOut,
    CronogramaEntregaIn,
    CronogramaEntregaOut,
    ProductoContratadoIn,
    ProductoContratadoOut,
)

router = APIRouter(prefix="/contratos", tags=["Contratos"])

ROLES_EDICION = ("ADMIN", "LOGISTICA_CENTRAL")

# RN-12: umbrales de alerta configurables vía parametro_sistema (Sesión 19)
# — 30 días / 15% si no están configurados (mismo valor que el hardcodeo
# original, ver Contrato.calcular_alerta_vigencia / ProductoContratado.
# calcular_alerta_saldo).
CLAVE_DIAS_ALERTA_VIGENCIA = "contratos_dias_alerta_vigencia"
CLAVE_PCT_ALERTA_SALDO = "contratos_pct_alerta_saldo"


def _build_detail(contrato, umbral_vigencia: int, umbral_saldo: int) -> ContratoDetailOut:
    base = ContratoListOut.from_model(contrato, umbral_vigencia)
    return ContratoDetailOut(
        **base.model_dump(),
        cronograma=[CronogramaEntregaOut.model_validate(c) for c in contrato.cronograma],
        productos_contratados=[
            ProductoContratadoOut.from_model(p, umbral_saldo) for p in contrato.productos_contratados
        ],
    )


@router.get("", response_model=Page[ContratoListOut])
async def listar_contratos(
    page: int = 1,
    page_size: int = 20,
    proveedor_id: int | None = None,
    estado: str | None = None,
    buscar: str | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> Page[ContratoListOut]:
    if current.rol == "PROVEEDOR":
        proveedor_id = current.proveedor_id
    items, total = await contrato_repo.list_filtrado(
        db, page=page, page_size=page_size, proveedor_id=proveedor_id, estado=estado, buscar=buscar
    )
    umbral_vigencia = await obtener_entero(db, CLAVE_DIAS_ALERTA_VIGENCIA, default=30)
    return Page(
        items=[ContratoListOut.from_model(c, umbral_vigencia) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{contrato_id}", response_model=ContratoDetailOut)
async def obtener_contrato(
    contrato_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> ContratoDetailOut:
    contrato = await contrato_repo.get_con_detalle(db, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato no encontrado")
    verificar_acceso_proveedor(current, contrato.proveedor_id)
    umbral_vigencia = await obtener_entero(db, CLAVE_DIAS_ALERTA_VIGENCIA, default=30)
    umbral_saldo = await obtener_entero(db, CLAVE_PCT_ALERTA_SALDO, default=15)
    return _build_detail(contrato, umbral_vigencia, umbral_saldo)


@router.post("", response_model=ContratoDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_contrato(
    data: ContratoCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ContratoDetailOut:
    try:
        contrato = await contrato_repo.crear(db, data, responsable_id=current.usuario_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El número de contrato ya existe")

    contrato = await contrato_repo.get_con_detalle(db, contrato.contrato_id)
    umbral_vigencia = await obtener_entero(db, CLAVE_DIAS_ALERTA_VIGENCIA, default=30)
    umbral_saldo = await obtener_entero(db, CLAVE_PCT_ALERTA_SALDO, default=15)
    return _build_detail(contrato, umbral_vigencia, umbral_saldo)


@router.patch("/{contrato_id}/estado", response_model=ContratoOut)
async def cambiar_estado_contrato(
    contrato_id: int,
    data: ContratoEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ContratoOut:
    contrato = await contrato_repo.get(db, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato no encontrado")

    try:
        contrato_repo.validar_transicion(contrato.estado, data.estado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    contrato.estado = data.estado
    await db.commit()
    await db.refresh(contrato)
    umbral_vigencia = await obtener_entero(db, CLAVE_DIAS_ALERTA_VIGENCIA, default=30)
    return ContratoOut.from_model(contrato, umbral_vigencia)


@router.post(
    "/{contrato_id}/cronograma", response_model=CronogramaEntregaOut, status_code=status.HTTP_201_CREATED
)
async def agregar_cronograma(
    contrato_id: int,
    data: CronogramaEntregaIn,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> CronogramaEntregaOut:
    contrato = await contrato_repo.get(db, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato no encontrado")

    entrega = await contrato_repo.agregar_cronograma(db, contrato_id, data)
    await db.commit()
    return entrega


@router.post(
    "/{contrato_id}/productos", response_model=ProductoContratadoOut, status_code=status.HTTP_201_CREATED
)
async def agregar_producto_contratado(
    contrato_id: int,
    data: ProductoContratadoIn,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ProductoContratadoOut:
    """RN-19: el saldo físico/monetario que aquí se inicializa es GLOBAL al
    contrato, independiente de cuántos almacenes reciban producto de él."""
    contrato = await contrato_repo.get(db, contrato_id)
    if contrato is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato no encontrado")

    try:
        producto_contratado = await contrato_repo.agregar_producto_contratado(db, contrato_id, data)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este producto ya está contratado en este contrato",
        )

    umbral_saldo = await obtener_entero(db, CLAVE_PCT_ALERTA_SALDO, default=15)
    return ProductoContratadoOut.from_model(producto_contratado, umbral_saldo)
