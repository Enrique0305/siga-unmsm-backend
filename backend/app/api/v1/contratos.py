from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles, verificar_acceso_proveedor
from app.crud.contrato import contrato_repo
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


def _build_detail(contrato) -> ContratoDetailOut:
    base = ContratoListOut.from_model(contrato)
    return ContratoDetailOut(
        **base.model_dump(),
        cronograma=[CronogramaEntregaOut.model_validate(c) for c in contrato.cronograma],
        productos_contratados=[ProductoContratadoOut.from_model(p) for p in contrato.productos_contratados],
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
    return Page(
        items=[ContratoListOut.from_model(c) for c in items],
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
    return _build_detail(contrato)


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
    return _build_detail(contrato)


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
    return contrato


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

    return ProductoContratadoOut.from_model(producto_contratado)
