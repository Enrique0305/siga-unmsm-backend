from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.catalogos import Alimento
from app.models.receta import Receta, RecetaIngrediente, RecetaValorNutricional
from app.schemas.receta import RecetaCreate

# Transiciones de estado válidas (Módulo 1A, sección 4.1A del diseño)
TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    "BORRADOR": {"EN_REVISION"},
    "EN_REVISION": {"APROBADO", "BORRADOR"},
    "APROBADO": {"VIGENTE", "DESCONTINUADO"},
    "VIGENTE": {"DESCONTINUADO"},
    "DESCONTINUADO": set(),
}

NUTRIENTES_RESUMEN = (
    "energia_kcal",
    "proteinas_g",
    "grasa_total_g",
    "carbohidratos_totales_g",
    "fibra_dietaria_g",
    "sodio_mg",
)
# Mapa nutriente-de-alimento -> campo totalizado en receta_valor_nutricional
MAPA_CAMPO_TOTAL = {
    "energia_kcal": "energia_kcal_total",
    "proteinas_g": "proteinas_g_total",
    "grasa_total_g": "grasa_total_g_total",
    "carbohidratos_totales_g": "carbohidratos_g_total",
    "fibra_dietaria_g": "fibra_g_total",
    "sodio_mg": "sodio_mg_total",
}
MAPA_CAMPO_RACION = {
    "energia_kcal": "energia_kcal_racion",
    "proteinas_g": "proteinas_g_racion",
    "grasa_total_g": "grasa_total_g_racion",
    "carbohidratos_totales_g": "carbohidratos_g_racion",
    "fibra_dietaria_g": "fibra_g_racion",
    "sodio_mg": "sodio_mg_racion",
}


class CRUDReceta(CRUDBase[Receta]):
    async def get_con_detalle(self, db: AsyncSession, receta_id: int) -> Receta | None:
        stmt = (
            select(Receta)
            .where(Receta.receta_id == receta_id)
            .options(
                selectinload(Receta.ingredientes)
                .selectinload(RecetaIngrediente.alimento)
                .selectinload(Alimento.versiones),
                selectinload(Receta.valor_nutricional),
            )
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    async def list_filtrado(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        estado: str | None = None,
        categoria_preparacion: str | None = None,
        buscar: str | None = None,
    ) -> tuple[list[Receta], int]:
        stmt = select(Receta)
        if estado:
            stmt = stmt.where(Receta.estado == estado)
        if categoria_preparacion:
            stmt = stmt.where(Receta.categoria_preparacion == categoria_preparacion)
        if buscar:
            like = f"%{buscar}%"
            stmt = stmt.where((Receta.nombre.ilike(like)) | (Receta.codigo.ilike(like)))
        return await self._paginar(db, stmt, page, page_size)

    async def _paginar(self, db, stmt, page, page_size):
        from sqlalchemy import func

        count_stmt = select(func.count()).select_from(stmt.with_only_columns(Receta.receta_id).subquery())
        total = (await db.execute(count_stmt)).scalar_one()
        stmt = stmt.order_by(Receta.nombre).offset((page - 1) * page_size).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()
        return list(items), total

    async def crear_con_ingredientes(self, db: AsyncSession, data: RecetaCreate, creado_por_id: int) -> Receta:
        receta = Receta(
            codigo=data.codigo,
            nombre=data.nombre,
            categoria_preparacion=data.categoria_preparacion,
            descripcion=data.descripcion,
            numero_raciones_base=data.numero_raciones_base,
            tamano_porcion_g=data.tamano_porcion_g,
            rendimiento_pct=data.rendimiento_pct,
            merma_estimada_pct=data.merma_estimada_pct,
            procedimiento=data.procedimiento,
            creado_por_id=creado_por_id,
        )
        db.add(receta)
        await db.flush()

        for ing in data.ingredientes:
            db.add(RecetaIngrediente(receta_id=receta.receta_id, **ing.model_dump()))
        await db.flush()

        await self.recalcular_nutricion(db, receta.receta_id)
        return receta

    async def recalcular_nutricion(self, db: AsyncSession, receta_id: int) -> RecetaValorNutricional:
        """
        Suma, sobre los ingredientes vigentes de la receta, el aporte
        nutricional proporcional a cantidad_neta_g (regla de tres sobre el
        valor por 100 g del alimento). Usa SIEMPRE la versión vigente del
        alimento (Alimento.version_vigente) — si el nutricionista corrige
        valores nutricionales, las recetas reflejan el cambio en el
        próximo recálculo, sin tocar la receta en sí.
        """
        receta = await self.get_con_detalle(db, receta_id)
        totales = {campo: 0.0 for campo in MAPA_CAMPO_TOTAL.values()}

        for ing in receta.ingredientes:
            vigente = ing.alimento.version_vigente
            if vigente is None:
                continue
            factor = ing.cantidad_neta_g / 100.0
            for campo_alimento, campo_total in MAPA_CAMPO_TOTAL.items():
                valor = getattr(vigente, campo_alimento, None) or 0.0
                totales[campo_total] += valor * factor

        raciones = receta.numero_raciones_base or 1
        valores_racion = {
            MAPA_CAMPO_RACION[campo_alim]: round(totales[campo_tot] / raciones, 4)
            for campo_alim, campo_tot in MAPA_CAMPO_TOTAL.items()
        }
        totales_redondeados = {k: round(v, 4) for k, v in totales.items()}

        existente = receta.valor_nutricional
        if existente is None:
            existente = RecetaValorNutricional(receta_id=receta_id)
            db.add(existente)
        for campo, valor in {**totales_redondeados, **valores_racion}.items():
            setattr(existente, campo, valor)

        await db.flush()
        # IMPORTANTE: `receta` fue cargado más arriba con selectinload(valor_nutricional),
        # que en ese momento aún no existía y quedó cacheado como None en el mapa de
        # identidad de la sesión. Sin este refresh, cualquier lectura posterior de
        # `receta.valor_nutricional` en la MISMA sesión seguiría devolviendo None
        # aunque la fila ya esté en la base de datos.
        await db.refresh(receta, attribute_names=["valor_nutricional"])
        return existente

    def validar_transicion(self, estado_actual: str, estado_nuevo: str) -> None:
        permitidos = TRANSICIONES_VALIDAS.get(estado_actual, set())
        if estado_nuevo not in permitidos:
            raise ValueError(f"No se puede pasar de '{estado_actual}' a '{estado_nuevo}'")

    async def crear_nueva_version(self, db: AsyncSession, receta_id: int, creado_por_id: int) -> Receta:
        """
        RN-25: una receta APROBADO/VIGENTE ya usada en un menú no se edita:
        se clona como nueva versión en BORRADOR, apuntando a la anterior
        vía receta_padre_id, con los mismos ingredientes como punto de
        partida para editar.
        """
        original = await self.get_con_detalle(db, receta_id)
        if original is None:
            raise ValueError("Receta no encontrada")

        nueva = Receta(
            codigo=original.codigo,
            nombre=original.nombre,
            categoria_preparacion=original.categoria_preparacion,
            descripcion=original.descripcion,
            numero_raciones_base=original.numero_raciones_base,
            tamano_porcion_g=original.tamano_porcion_g,
            rendimiento_pct=original.rendimiento_pct,
            merma_estimada_pct=original.merma_estimada_pct,
            procedimiento=original.procedimiento,
            version=original.version + 1,
            receta_padre_id=original.receta_id,
            estado="BORRADOR",
            creado_por_id=creado_por_id,
        )
        db.add(nueva)
        await db.flush()

        for ing in original.ingredientes:
            db.add(
                RecetaIngrediente(
                    receta_id=nueva.receta_id,
                    alimento_id=ing.alimento_id,
                    cantidad_bruta_g=ing.cantidad_bruta_g,
                    cantidad_neta_g=ing.cantidad_neta_g,
                    unidad_id=ing.unidad_id,
                    factor_conversion=ing.factor_conversion,
                    merma_pct=ing.merma_pct,
                )
            )
        await db.flush()
        await self.recalcular_nutricion(db, nueva.receta_id)
        return nueva


receta_repo = CRUDReceta(Receta)
