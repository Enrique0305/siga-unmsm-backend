from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, require_roles
from app.crud.parametro_sistema import eliminar, list_todos, upsert
from app.db.session import get_db
from app.schemas.sistema import ParametroSistemaIn, ParametroSistemaOut

router = APIRouter(prefix="/parametros-sistema", tags=["Parámetros del sistema"])

# Respaldado por la tabla de roles del diseño original: "Administrador del
# sistema | Todos (config.) | Catálogos, usuarios, roles, parámetros,
# auditoría" — a diferencia de otros catálogos/parámetros (productos,
# stock por almacén), este es exclusivo de ADMIN, ni LOGISTICA_CENTRAL.
ROLES_EDICION = ("ADMIN",)


@router.get("", response_model=list[ParametroSistemaOut])
async def listar_parametros(
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(get_current_user),
) -> list[ParametroSistemaOut]:
    parametros = await list_todos(db)
    return [ParametroSistemaOut.model_validate(p) for p in parametros]


@router.put("", response_model=ParametroSistemaOut)
async def upsert_parametro(
    data: ParametroSistemaIn,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> ParametroSistemaOut:
    parametro = await upsert(db, data, actualizado_por_id=current.usuario_id)
    await db.commit()
    await db.refresh(parametro)
    return ParametroSistemaOut.model_validate(parametro)


@router.delete("/{clave}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_parametro(
    clave: str,
    db: AsyncSession = Depends(get_db),
    _current: CurrentUser = Depends(require_roles(*ROLES_EDICION)),
) -> None:
    eliminado = await eliminar(db, clave)
    if not eliminado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parámetro no encontrado")
    await db.commit()
