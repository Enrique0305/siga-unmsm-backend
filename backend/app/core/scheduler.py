"""
Scheduler in-process (Sesión 20) — corre dentro del proceso `api` vía el
lifespan de FastAPI (app/main.py), no hay servicio worker separado en
docker-compose.yml (una sola instancia, sin réplicas, agregar un
contenedor aparte sería sobre-ingeniería para este tamaño).

Horas fijas, sin volverlas configurables (RN-11/RN-12 no lo piden).
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.jobs import procesar_actas_vencidas, procesar_alertas_contratos
from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _ejecutar_procesar_actas_vencidas() -> None:
    async with AsyncSessionLocal() as db:
        resultado = await procesar_actas_vencidas(db)
        await db.commit()
        logger.info("RN-11 procesar_actas_vencidas: %s", resultado)


async def _ejecutar_procesar_alertas_contratos() -> None:
    async with AsyncSessionLocal() as db:
        resultado = await procesar_alertas_contratos(db)
        await db.commit()
        logger.info("RN-12 procesar_alertas_contratos: %s", resultado)


def iniciar_scheduler() -> None:
    scheduler.add_job(_ejecutar_procesar_actas_vencidas, "cron", hour=2, minute=0, id="rn11_actas_vencidas")
    scheduler.add_job(_ejecutar_procesar_alertas_contratos, "cron", hour=3, minute=0, id="rn12_alertas_contratos")
    scheduler.start()


def detener_scheduler() -> None:
    scheduler.shutdown(wait=False)
