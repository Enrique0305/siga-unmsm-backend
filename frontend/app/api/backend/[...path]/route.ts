import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  accessTokenCookieOptions,
  refreshTokenCookieOptions,
} from "@/lib/auth/cookies";

/**
 * Reenvía cualquier request de un Client Component (hooks orval/TanStack
 * Query, que no pueden leer la cookie httpOnly) hacia FastAPI, agregando
 * el Bearer token. Si FastAPI responde 401, intenta UN refresh automático
 * antes de reintentar una vez (ver arquitectura de dos caminos en el plan
 * de la sesión — esto es la mitad "Client Component" de ese diseño).
 */
const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";
// Las URLs que genera orval ya incluyen el prefijo `/api/v1` (vienen del
// OpenAPI del backend, ej. `/api/v1/proveedores`), y ese prefijo queda
// capturado dentro de `path` (todo lo que sigue a `/api/backend/`). Por
// eso acá se usa el origen pelado, no `API_URL` (que ya trae `/api/v1`
// para los demás usos de este archivo) — si no, el prefijo queda duplicado.
const API_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, "");

async function forwardToBackend(
  request: NextRequest,
  path: string[],
  accessToken: string | undefined,
) {
  const search = request.nextUrl.search;
  const url = `${API_ORIGIN}/${path.join("/")}${search}`;
  const hasBody = !["GET", "HEAD"].includes(request.method);

  return fetch(url, {
    method: request.method,
    headers: {
      "Content-Type": request.headers.get("content-type") ?? "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
  });
}

async function refreshTokens(refreshToken: string) {
  const response = await fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as {
    access_token: string;
    refresh_token: string;
  };
}

async function handler(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const cookieStore = await cookies();
  let accessToken = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;

  let backendResponse = await forwardToBackend(request, path, accessToken);

  if (backendResponse.status === 401) {
    const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;
    const renewed = refreshToken ? await refreshTokens(refreshToken) : null;

    if (renewed) {
      accessToken = renewed.access_token;
      cookieStore.set(
        ACCESS_TOKEN_COOKIE,
        renewed.access_token,
        accessTokenCookieOptions,
      );
      cookieStore.set(
        REFRESH_TOKEN_COOKIE,
        renewed.refresh_token,
        refreshTokenCookieOptions,
      );
      backendResponse = await forwardToBackend(request, path, accessToken);
    } else {
      cookieStore.delete(ACCESS_TOKEN_COOKIE);
      cookieStore.delete(REFRESH_TOKEN_COOKIE);
    }
  }

  // 204/205/304 no pueden llevar body (spec Fetch/Response) — construir
  // NextResponse con un ArrayBuffer vacío igual revienta en tiempo de
  // ejecución. Detectado en la Sesión 17: DELETE /parametros-stock es el
  // primer endpoint de todo el backend que responde 204.
  const responseBody =
    backendResponse.status === 204 || backendResponse.status === 205 || backendResponse.status === 304
      ? null
      : await backendResponse.arrayBuffer();
  return new NextResponse(responseBody, {
    status: backendResponse.status,
    headers: {
      "Content-Type":
        backendResponse.headers.get("content-type") ?? "application/json",
    },
  });
}

export {
  handler as GET,
  handler as POST,
  handler as PATCH,
  handler as PUT,
  handler as DELETE,
};
