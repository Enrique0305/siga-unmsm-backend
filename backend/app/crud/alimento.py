from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.catalogos import Alimento, AlimentoVersion
from app.schemas.alimento import AlimentoVersionCreate


class CRUDAlimento(CRUDBase[Alimento]):
    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        categoria_alimento_id: int | None = None,
        tipo: str | None = None,
        estado: str | None = None,
        buscar: str | None = None,
    ) -> tuple[list[Alimento], int]:
        stmt = select(Alimento).options(
            selectinload(Alimento.categoria),
            selectinload(Alimento.versiones),
        )
        if categoria_alimento_id is not None:
            stmt = stmt.where(Alimento.categoria_alimento_id == categoria_alimento_id)
        if tipo is not None:
            stmt = stmt.where(Alimento.tipo == tipo)
        if estado is not None:
            stmt = stmt.where(Alimento.estado == estado)
        if buscar:
            like = f"%{buscar}%"
            stmt = stmt.where((Alimento.nombre.ilike(like)) | (Alimento.codigo.ilike(like)))

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Alimento.alimento_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Alimento.nombre).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().unique().all()
        return list(items), total

    async def get_con_versiones(self, db: AsyncSession, alimento_id: int) -> Alimento | None:
        stmt = (
            select(Alimento)
            .where(Alimento.alimento_id == alimento_id)
            .options(selectinload(Alimento.categoria), selectinload(Alimento.versiones))
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def crear_nueva_version(
        self,
        db: AsyncSession,
        alimento_id: int,
        data: AlimentoVersionCreate,
        editado_por_id: int,
    ) -> AlimentoVersion:
        """
        Aplica RN-25/RN-26: nunca sobre-escribe una versión existente.
        NOTA: en MySQL esto NO se hace con un trigger (ver 08_parche_fix_
        trigger_alimento_version.sql) — la unicidad de 'vigente' la protege
        el índice único generado `vigente_key`; aquí se hace explícito el
        orden UPDATE -> INSERT dentro de la misma transacción.
        """
        # 1) baja la versión vigente actual (si existe)
        stmt = select(AlimentoVersion).where(
            AlimentoVersion.alimento_id == alimento_id, AlimentoVersion.vigente.is_(True)
        )
        actual = (await db.execute(stmt)).scalar_one_or_none()
        siguiente_version = 1
        if actual is not None:
            siguiente_version = actual.version + 1
            actual.vigente = False
            db.add(actual)
            await db.flush()

        # 2) inserta la nueva versión vigente
        nueva = AlimentoVersion(
            alimento_id=alimento_id,
            version=siguiente_version,
            fuente=data.fuente,
            fecha_importacion=date.today(),
            vigente=True,
            editado_por_id=editado_por_id,
            **data.model_dump(exclude={"fuente"}),
        )
        db.add(nueva)
        await db.flush()
        return nueva


alimento_repo = CRUDAlimento(Alimento)
