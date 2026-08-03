# SIGA-UNMSM — Frontend (Next.js)

Consume la API de FastAPI ya construida (ver `../README.md`). Next.js 16
(App Router, TypeScript, Tailwind v4) con un cliente generado desde el
OpenAPI del backend para no duplicar a mano los schemas de Pydantic.

## Arquitectura

- **Autenticación**: patrón BFF. `POST /api/auth/login` (route handler)
  llama a `POST /auth/login` de FastAPI y guarda `access_token`/
  `refresh_token` en cookies `httpOnly` — el JWT nunca es visible a JS del
  navegador. `proxy.ts` (Next.js 16 renombró `middleware.ts` → `proxy.ts`)
  redirige a `/login` si no hay cookie de sesión.
- **Dos caminos para llamar a la API**, según el tipo de componente:
  - **Server Components** (páginas de solo lectura, como el Dashboard):
    `lib/api/server-fetch.ts` lee la cookie con `next/headers` y llama a
    FastAPI directo, server-to-server.
  - **Client Components** (formularios, hooks de TanStack Query generados
    por `orval`): no pueden leer la cookie httpOnly, así que pasan por
    `app/api/backend/[...path]/route.ts`, que reenvía el request con el
    Bearer token y hace **un** refresh automático si FastAPI responde 401.
- El JWT se decodifica en el servidor (`lib/auth/session.ts`, con `jose`)
  solo para pintar el rol en el sidebar — **no se verifica la firma** en el
  frontend. La autorización real siempre la hace FastAPI en cada request.

## Arranque rápido

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run generate:api   # regenera lib/api/generated/ desde el openapi.json del backend
npm run dev
```

Requiere el backend corriendo en `http://localhost:8000` (ver
`../README.md`) y el seed inicial ya ejecutado
(`docker compose exec api python -m app.seed`) para tener un usuario con
el cual iniciar sesión.

Con Docker (los 3 servicios juntos): `docker compose up --build` desde la
raíz del repo.

## Regenerar el cliente API

Cualquier cambio en los endpoints de FastAPI requiere volver a correr
`npm run generate:api` (backend corriendo) y commitear el resultado en
`lib/api/generated/` — es código generado determinístico, se versiona
igual que cualquier otro archivo fuente, no se regenera en cada build.

## Estructura

```
app/
  login/page.tsx              Formulario de login (Client Component)
  (dashboard)/layout.tsx       Shell autenticado: Sidebar + Topbar (Server Component)
  (dashboard)/page.tsx         Dashboard ejecutivo con KPIs reales
  api/auth/login/route.ts      Route handler: login + set cookies httpOnly
  api/auth/logout/route.ts     Route handler: logout + clear cookies
  api/backend/[...path]/route.ts  BFF: reenvía requests de Client Components a FastAPI
proxy.ts                       Guard de sesión (redirige a /login)
lib/api/mutator.ts             Mutator usado por los hooks orval (Client Components)
lib/api/server-fetch.ts        Fetch directo para Server Components
lib/api/generated/             Cliente generado por orval — no editar a mano
lib/auth/                      Cookies, sesión (decodificación JWT sin verificar firma)
lib/nav.ts                     Mapa del sitio filtrado por rol (sidebar)
components/layout/             Sidebar, Topbar
components/ui/                 Componentes reusables (StatCard, ...)
components/providers/          QueryProvider (TanStack Query)
```

## Estado actual (Sesión 1)

Implementado: scaffold, tema con la paleta institucional, cliente API
(orval + TanStack Query), autenticación completa, shell con sidebar
filtrado por rol, Dashboard con KPIs reales.

Pendiente (sesiones futuras, mismo patrón: Server Component de lista +
Client Component de formulario con hooks `orval`): las ~23 pantallas
restantes del catálogo (Planificación, Contratos, Compras, Recepción/
Calidad, Almacenes, Cocina, Conformidad/Pagos, Reportes, Administración),
tests automatizados de frontend, build de producción multi-stage.
