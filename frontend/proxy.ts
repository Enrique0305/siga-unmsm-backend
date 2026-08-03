import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE } from "@/lib/auth/cookies";

/**
 * Next.js 16 renombró `middleware.ts`/`export function middleware()` a
 * `proxy.ts`/`export function proxy()` (misma API, mismo `config.matcher`).
 * Solo valida PRESENCIA de la cookie de sesión para redirigir a /login —
 * la autorización real (rol, expiración, firma) la sigue validando FastAPI
 * en cada request; un 401 real durante el uso normal lo maneja el route
 * handler `app/api/backend/[...path]/route.ts` (refresh-on-401).
 */
export function proxy(request: NextRequest) {
  const hasSession = request.cookies.has(ACCESS_TOKEN_COOKIE);
  const isLoginPage = request.nextUrl.pathname === "/login";

  if (!hasSession && !isLoginPage) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (hasSession && isLoginPage) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
