import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  accessTokenCookieOptions,
  refreshTokenCookieOptions,
} from "@/lib/auth/cookies";

const API_URL = process.env.API_URL ?? "http://localhost:8000/api/v1";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  if (!body?.correo || !body?.password) {
    return NextResponse.json(
      { detail: "correo y password son requeridos" },
      { status: 422 },
    );
  }

  const backendResponse = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ correo: body.correo, password: body.password }),
  });

  if (!backendResponse.ok) {
    const detail = await backendResponse.json().catch(() => null);
    return NextResponse.json(
      detail ?? { detail: "No se pudo iniciar sesión" },
      { status: backendResponse.status },
    );
  }

  const { access_token: accessToken, refresh_token: refreshToken } =
    await backendResponse.json();

  const cookieStore = await cookies();
  cookieStore.set(ACCESS_TOKEN_COOKIE, accessToken, accessTokenCookieOptions);
  cookieStore.set(
    REFRESH_TOKEN_COOKIE,
    refreshToken,
    refreshTokenCookieOptions,
  );

  return NextResponse.json({ ok: true });
}
