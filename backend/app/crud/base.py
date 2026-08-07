from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    """
    Repositorio genérico con las operaciones comunes. Los repositorios de
    cada módulo (usuario, almacen, alimento, ...) heredan de esta clase y
    agregan solo lo específico (filtros de negocio, validaciones RN-xx).
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, pk: Any) -> ModelType | None:
        return await db.get(self.model, pk)

    async def list_paginated(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        **filters: Any,
    ) -> tuple[list[ModelType], int]:
        stmt = select(self.model)
        for field, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(self.model, field) == value)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def create(self, db: AsyncSession, obj_in: dict[str, Any]) -> ModelType:
        obj = self.model(**obj_in)
        db.add(obj)
        await db.flush()
        # Refresca columnas con server_default/Computed (ej. creado_en) tras
        # el INSERT — en MySQL/aiomysql quedan "expiradas" sin esto, y
        # serializarlas fuera de un await revienta con MissingGreenlet
        # (CLAUDE.md gotcha #7.3). Invisible en SQLite (los tests resuelven
        # RETURNING distinto), por eso ningún test lo detectó.
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, pk: Any) -> None:
        obj = await self.get(db, pk)
        if obj is not None:
            await db.delete(obj)
            await db.flush()
