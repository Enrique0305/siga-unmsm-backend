from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.alimento import alimento_repo
from app.db.session import get_db
from app.schemas.alimento import (
    AlimentoCreate,
    AlimentoDetailOut,
    AlimentoListOut,
    AlimentoVersionCreate,
    AlimentoVersionOut,
)
from app.schemas.common import Page

router = APIRouter(prefix="/alimentos", tags=["Catálogo nutricional"])

# Cualquier usuario autenticado puede CONSULTAR el catálogo (recetas,
# cocina, logística, etc. lo necesitan). Solo el Nutricionista autorizado
# y el Administrador pueden crear alimentos o nuevas versiones (RN-26).
ROLES_EDICION = ("ADMIN", "NUTRICION")


@router.get("", response_model=Page[AlimentoListOut])
async def listar_alimentos(
    page: int = 1,
    page_size: int = 20,
    categoria_alimento_id: int | None = None,
    tipo: str | None = None,
    estado: str | None = "ACTIVO",
    buscar: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> Page[AlimentoListOut]:
    items, total = await alimento_repo.list_filtrado(
        db,
        page=page,
        page_size=page_size,
        categoria_alimento_id=categoria_alimento_id,
        tipo=tipo,
        estado=estado,
        buscar=buscar,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{alimento_id}", response_model=AlimentoDetailOut)
async def obtener_alimento(
    alimento_id: int,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> AlimentoDetailOut:
    alimento = await alimento_repo.get_con_versiones(db, alimento_id)
    if alimento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alimento no encontrado")
    return alimento


@router.post("", response_model=AlimentoDetailOut, status_code=status.HTTP_201_CREATED)
async def crear_alimento(
    data: AlimentoCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> AlimentoDetailOut:
    try:
        alimento = await alimento_repo.create(
            db,
            {
                "codigo": data.codigo,
                "nombre": data.nombre,
                "categoria_alimento_id": data.categoria_alimento_id,
                "tipo": data.tipo,
                "creado_por_id": current.usuario_id,
            },
        )
        await alimento_repo.crear_nueva_version(
            db,
            alimento.alimento_id,
            AlimentoVersionCreate(fuente=data.fuente, **data.valores.model_dump()),
            editado_por_id=current.usuario_id,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El código de alimento ya existe")

    return await alimento_repo.get_con_versiones(db, alimento.alimento_id)


@router.post("/{alimento_id}/versiones", response_model=AlimentoVersionOut, status_code=status.HTTP_201_CREATED)
async def corregir_valores_nutricionales(
    alimento_id: int,
    data: AlimentoVersionCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> AlimentoVersionOut:
    """
    RN-25/RN-26: el nutricionista corrige valores → se crea una NUEVA
    versión vigente; la anterior queda en el historial (nunca se borra).
    """
    alimento = await alimento_repo.get(db, alimento_id)
    if alimento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alimento no encontrado")

    nueva_version = await alimento_repo.crear_nueva_version(db, alimento_id, data, editado_por_id=current.usuario_id)
    await db.commit()
    await db.refresh(nueva_version)
    return nueva_version
