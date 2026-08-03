/**
 * Mutator usado por los hooks de TanStack Query generados por orval
 * (`orval.config.ts`). Corre en el navegador: nunca ve el JWT (vive en una
 * cookie httpOnly) — reenvía todo a través del route handler
 * `app/api/backend/[...path]/route.ts`, que sí puede leer la cookie.
 */
export const apiFetch = async <T>(
  url: string,
  options?: RequestInit,
): Promise<T> => {
  const response = await fetch(`/api/backend${url}`, {
    ...options,
    credentials: "include",
  });

  const contentType = response.headers.get("content-type");
  const data = contentType?.includes("application/json")
    ? await response.json()
    : await response.text();

  return {
    status: response.status,
    data,
    headers: response.headers,
  } as T;
};

export default apiFetch;
