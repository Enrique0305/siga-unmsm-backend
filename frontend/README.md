# Frontend (Next.js) — próxima etapa

Por acuerdo del equipo, el backend (FastAPI) se construye primero y
completo; el frontend en Next.js arranca después, consumiendo la API ya
probada.

Cuando empecemos esta etapa:
1. `npx create-next-app@latest . --typescript --tailwind --app`
2. Generar el cliente TypeScript desde `http://localhost:8000/api/v1/openapi.json`
   (con `openapi-typescript` u `orval`) para no duplicar los schemas de Pydantic a mano.
3. Estructura de rutas alineada al catálogo de 24 pantallas ya definido en
   `01_diseno_sistema_SIGA-UNMSM.md` (Dashboard, Planificación, Contratos,
   Órdenes de Compra, Almacenes/Transferencias, Recetas, etc.)
4. Descomentar el servicio `frontend` en `docker-compose.yml` una vez exista
   el `Dockerfile` aquí.
