export const ACCESS_TOKEN_COOKIE = "siga_access_token";
export const REFRESH_TOKEN_COOKIE = "siga_refresh_token";

type CookieOptions = {
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: "lax" | "strict" | "none";
  path?: string;
  maxAge?: number;
};

const isProduction = process.env.NODE_ENV === "production";

const baseOptions: CookieOptions = {
  httpOnly: true,
  secure: isProduction,
  sameSite: "lax",
  path: "/",
};

// Coincide con ACCESS_TOKEN_EXPIRE_MINUTES / REFRESH_TOKEN_EXPIRE_DAYS
// en backend/app/core/config.py — si cambian ahí, ajustar aquí también.
export const accessTokenCookieOptions: CookieOptions = {
  ...baseOptions,
  maxAge: 30 * 60,
};

export const refreshTokenCookieOptions: CookieOptions = {
  ...baseOptions,
  maxAge: 7 * 24 * 60 * 60,
};
