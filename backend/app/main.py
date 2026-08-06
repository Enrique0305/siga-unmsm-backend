from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.audit  # noqa: F401  registra el evento de auditoría (RN-08)
from app.api.middleware import AuditContextMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.scheduler import detener_scheduler, iniciar_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Jobs automáticos RN-11/RN-12 (Sesión 20) — in-process, ver core/scheduler.py.
    # httpx.ASGITransport (usado por toda la suite de tests) no dispara el
    # lifespan por defecto, así que los tests nunca arrancan el scheduler real.
    iniciar_scheduler()
    yield
    detener_scheduler()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "API del Sistema Integral de Gestión de Almacén y Abastecimiento "
        "Alimentario — UNMSM. Cubre planificación nutricional, contratos y "
        "compras, recepción e inspección, almacén multialmacén, cocina/"
        "consumo, conformidad y pagos, y reportes/auditoría/administración."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    lifespan=lifespan,
)

app.add_middleware(AuditContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Sistema"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
