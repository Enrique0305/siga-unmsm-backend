from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.audit  # noqa: F401  registra el evento de auditoría (RN-08)
from app.api.middleware import AuditContextMiddleware
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    description=(
        "API del Sistema Integral de Gestión de Almacén y Abastecimiento "
        "Alimentario — UNMSM. Módulos activos: Autenticación, Usuarios, "
        "Almacenes, Catálogo Nutricional."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
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
