from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.bom_consolidado import servicio_bom_consolidado
from app.crud.dosificacion import servicio_dosificacion
from app.crud.planificacion import menu_dia_repo, menu_quincenal_repo, racion_anual_repo
from app.db.session import get_db
from app.models.planificacion import MenuDia
from app.schemas.common import Page
from app.schemas.dosificacion import BomConsolidadoOut, DosificacionDetalleOut
from app.schemas.planificacion import (
    MenuDiaCreate,
    MenuDiaDetailOut,
    MenuDiaOut,
    MenuQuincenalCreate,
    MenuQuincenalDetailOut,
    MenuQuincenalEstadoUpdate,
    MenuQuincenalOut,
    PlatoCreate,
    PlatoOut,
    RacionAnualCreate,
    RacionAnualEstadoUpdate,
    RacionAnualOut,
)
from app.schemas.requerimiento import (
    RequerimientoAnualDetailOut,
    RequerimientoAnualDetalleOut,
    RequerimientoAnualOut,
)

router = APIRouter(prefix="/planificacion", tags=["Planificación / Menús"])
ROLES_EDICION = ("ADMIN", "NUTRICION")


# ---------------------------------------------------------------- raciones
@router.get("/raciones-anuales", response_model=Page[RacionAnualOut])
async def listar_raciones_anuales(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[RacionAnualOut]:
    items, total = await racion_anual_repo.list_paginated(db, page=page, page_size=page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/raciones-anuales", response_model=RacionAnualOut, status_code=status.HTTP_201_CREATED)
async def crear_racion_anual(
    data: RacionAnualCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RacionAnualOut:
    racion = await racion_anual_repo.create(db, {**data.model_dump(), "creado_por_id": current.usuario_id})
    await db.commit()
    return racion


@router.get("/raciones-anuales/{racion_anual_id}", response_model=RacionAnualOut)
async def obtener_racion_anual(
    racion_anual_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> RacionAnualOut:
    racion = await racion_anual_repo.get(db, racion_anual_id)
    if racion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ración anual no encontrada")
    return racion


@router.patch("/raciones-anuales/{racion_anual_id}/estado", response_model=RacionAnualOut)
async def cambiar_estado_racion_anual(
    racion_anual_id: int,
    data: RacionAnualEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RacionAnualOut:
    racion = await racion_anual_repo.get(db, racion_anual_id)
    if racion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ración anual no encontrada")

    try:
        racion_anual_repo.validar_transicion(racion.estado, data.estado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    racion_anual_repo.aplicar_transicion(racion, data.estado)
    await db.commit()
    await db.refresh(racion)
    return racion


@router.post(
    "/raciones-anuales/{racion_anual_id}/consolidar-requerimiento",
    response_model=RequerimientoAnualDetailOut,
    status_code=status.HTTP_201_CREATED,
    summary="Consolida la dosificación (BOM) ya calculada de toda la ración anual en un Requerimiento Anual",
)
async def consolidar_requerimiento(
    racion_anual_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> RequerimientoAnualDetailOut:
    try:
        requerimiento = await servicio_bom_consolidado.generar_y_consolidar(db, racion_anual_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    base = RequerimientoAnualOut.model_validate(requerimiento)
    return RequerimientoAnualDetailOut(
        **base.model_dump(),
        detalle=[RequerimientoAnualDetalleOut.from_model(d) for d in requerimiento.detalle],
    )


@router.get(
    "/raciones-anuales/{racion_anual_id}/bom-consolidado",
    response_model=list[BomConsolidadoOut],
    summary="Desglose por almacén de la última consolidación BOM generada para esta ración anual",
)
async def obtener_bom_consolidado(
    racion_anual_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> list[BomConsolidadoOut]:
    try:
        filas = await servicio_bom_consolidado.obtener_ultimo(db, racion_anual_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [BomConsolidadoOut.from_model(f) for f in filas]


# ------------------------------------------------------------ menú quincenal
@router.get("/menus-quincenales", response_model=Page[MenuQuincenalOut])
async def listar_menus_quincenales(
    page: int = 1,
    page_size: int = 20,
    racion_anual_id: int | None = None,
    estado: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[MenuQuincenalOut]:
    items, total = await menu_quincenal_repo.list_paginated(
        db, page=page, page_size=page_size, racion_anual_id=racion_anual_id, estado=estado
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/menus-quincenales", response_model=MenuQuincenalOut, status_code=status.HTTP_201_CREATED)
async def crear_menu_quincenal(
    data: MenuQuincenalCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> MenuQuincenalOut:
    menu = await menu_quincenal_repo.create(db, data.model_dump())
    await db.commit()
    return menu


@router.get("/menus-quincenales/{menu_id}", response_model=MenuQuincenalDetailOut)
async def obtener_menu_quincenal(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> MenuQuincenalDetailOut:
    menu = await menu_quincenal_repo.get_con_dias(db, menu_id)
    if menu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menú quincenal no encontrado")
    return MenuQuincenalDetailOut(
        menu_id=menu.menu_id,
        racion_anual_id=menu.racion_anual_id,
        quincena_inicio=menu.quincena_inicio,
        quincena_fin=menu.quincena_fin,
        version=menu.version,
        estado=menu.estado,
        aprobado_por_id=menu.aprobado_por_id,
        aprobado_en=menu.aprobado_en,
        creado_en=menu.creado_en,
        dias=list(menu.dias),
    )


@router.patch("/menus-quincenales/{menu_id}/estado", response_model=MenuQuincenalOut)
async def cambiar_estado_menu_quincenal(
    menu_id: int,
    data: MenuQuincenalEstadoUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION, "LOGISTICA_CENTRAL")),
) -> MenuQuincenalOut:
    menu = await menu_quincenal_repo.get(db, menu_id)
    if menu is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menú quincenal no encontrado")

    try:
        menu_quincenal_repo.validar_transicion(menu.estado, data.estado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    menu_quincenal_repo.aplicar_transicion(menu, data.estado, aprobado_por_id=current.usuario_id)
    await db.commit()
    await db.refresh(menu)
    return menu


@router.get("/menus-quincenales/{menu_id}/dias", response_model=list[MenuDiaOut])
async def listar_dias_menu(
    menu_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> list[MenuDia]:
    items, _ = await menu_dia_repo.list_paginated(db, page=1, page_size=100, menu_id=menu_id)
    return items


@router.post("/menus-quincenales/{menu_id}/dias", response_model=MenuDiaOut, status_code=status.HTTP_201_CREATED)
async def crear_dia_menu(
    menu_id: int,
    data: MenuDiaCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> MenuDiaOut:
    dia = await menu_dia_repo.create(db, {**data.model_dump(), "menu_id": menu_id})
    await db.commit()
    return dia


# -------------------------------------------------------------------- platos
@router.get("/dias/{menu_dia_id}", response_model=MenuDiaDetailOut)
async def obtener_dia_con_platos(
    menu_dia_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> MenuDiaDetailOut:
    dia = await menu_dia_repo.get_con_platos(db, menu_dia_id)
    if dia is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Día de menú no encontrado")
    return MenuDiaDetailOut(
        menu_dia_id=dia.menu_dia_id,
        menu_id=dia.menu_id,
        fecha=dia.fecha,
        tipo_servicio=dia.tipo_servicio,
        raciones_programadas=dia.raciones_programadas,
        platos=[PlatoOut.from_model(p) for p in dia.platos],
    )


@router.post("/dias/{menu_dia_id}/platos", response_model=PlatoOut, status_code=status.HTTP_201_CREATED)
async def agregar_plato_a_dia(
    menu_dia_id: int,
    data: PlatoCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> PlatoOut:
    """RN-22 se valida dentro de menu_dia_repo.agregar_plato: solo recetas VIGENTE."""
    try:
        plato = await menu_dia_repo.agregar_plato(db, menu_dia_id, data.receta_id, data.raciones_override)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return PlatoOut.from_model(plato)


# ------------------------------------------------------- dosificación (BOM)
@router.post(
    "/dias/{menu_dia_id}/dosificacion",
    response_model=list[DosificacionDetalleOut],
    summary="Calcula (o recalcula) la explosión de materiales de un día de menú para un comedor/almacén",
)
async def calcular_dosificacion(
    menu_dia_id: int,
    centro_consumo_id: int,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION, "LOGISTICA_CENTRAL")),
) -> list[DosificacionDetalleOut]:
    try:
        filas = await servicio_dosificacion.calcular_dia(db, menu_dia_id, centro_consumo_id)
        await db.commit()
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return [DosificacionDetalleOut.from_model(f) for f in filas]


@router.get("/dias/{menu_dia_id}/dosificacion", response_model=list[DosificacionDetalleOut])
async def obtener_dosificacion(
    menu_dia_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> list[DosificacionDetalleOut]:
    filas = await servicio_dosificacion.consolidar_por_almacen(db, menu_dia_id)
    return [DosificacionDetalleOut.from_model(f) for f in filas]
