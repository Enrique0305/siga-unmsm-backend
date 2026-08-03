import { cookies } from "next/headers";

import { ACCESS_TOKEN_COOKIE } from "@/lib/auth/cookies";

/**
 * Solo para Server Components (Dashboard y futuras pantallas de solo
 * lectura): lee la cookie httpOnly directo con `next/headers` y llama a
 * FastAPI server-to-server, sin pasar por `app/api/backend/[...path]`
 * (ese route handler es para Client Components, que no pueden leer cookies).
 */
const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";

export class ServerFetchError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(`API error ${status}`);
    this.name = "ServerFetchError";
  }
}

export async function serverFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    throw new ServerFetchError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
