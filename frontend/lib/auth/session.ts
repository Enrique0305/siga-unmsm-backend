import { decodeJwt } from "jose";
import { cookies } from "next/headers";

import { ACCESS_TOKEN_COOKIE } from "@/lib/auth/cookies";

/**
 * Mismos claims que pone `core/security.py::create_access_token` en el
 * backend. No se verifica la firma acá — solo se decodifica para pintar
 * el sidebar/rol en el servidor. La autorización real la hace siempre
 * FastAPI en cada request (ver justificación en el plan de la sesión).
 */
export type Session = {
  usuarioId: number;
  rol: string;
  almacenes: number[];
  accesoTodosAlmacenes: boolean;
};

type AccessTokenPayload = {
  sub: string;
  rol: string;
  almacenes: number[];
  acceso_todos_almacenes: boolean;
  type: "access" | "refresh";
  exp: number;
};

export async function getSession(): Promise<Session | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;
  if (!token) {
    return null;
  }

  try {
    const payload = decodeJwt<AccessTokenPayload>(token);
    return {
      usuarioId: Number(payload.sub),
      rol: payload.rol,
      almacenes: payload.almacenes,
      accesoTodosAlmacenes: payload.acceso_todos_almacenes,
    };
  } catch {
    return null;
  }
}
