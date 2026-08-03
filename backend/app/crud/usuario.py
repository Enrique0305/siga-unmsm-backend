from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.crud.base import CRUDBase
from app.models.organizacion import UsuarioAlmacenAcceso
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioCreate


class CRUDUsuario(CRUDBase[Usuario]):
    async def get_by_correo(self, db: AsyncSession, correo: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.correo == correo).options(selectinload(Usuario.rol))
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_almacen_ids(self, db: AsyncSession, usuario_id: int) -> list[int]:
        stmt = select(UsuarioAlmacenAcceso.almacen_id).where(UsuarioAlmacenAcceso.usuario_id == usuario_id)
        return list((await db.execute(stmt)).scalars().all())

    async def create_con_almacenes(self, db: AsyncSession, data: UsuarioCreate) -> Usuario:
        usuario = Usuario(
            nombres=data.nombres,
            apellidos=data.apellidos,
            correo=data.correo,
            password_hash=hash_password(data.password),
            rol_id=data.rol_id,
            sede_id=data.sede_id,
        )
        db.add(usuario)
        await db.flush()  # asigna usuario_id

        for almacen_id in data.almacen_ids:
            db.add(UsuarioAlmacenAcceso(usuario_id=usuario.usuario_id, almacen_id=almacen_id))
        await db.flush()
        return usuario


usuario_repo = CRUDUsuario(Usuario)
