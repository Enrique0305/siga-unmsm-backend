/**
 * FastAPI devuelve `{detail: string}` en errores simples (403/404/409) y
 * `{detail: ValidationError[]}` en 422 (ver `HTTPValidationError` en
 * lib/api/generated/model). El mutator no lanza excepción en 4xx/5xx —
 * los formularios llaman esto a mano con `response.data`.
 */
export function extractErrorMessage(data: unknown): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((err) => {
          if (err && typeof err === "object" && "msg" in err) {
            const loc = Array.isArray((err as { loc?: unknown }).loc)
              ? (err as { loc: unknown[] }).loc.join(".")
              : undefined;
            const msg = String((err as { msg: unknown }).msg);
            return loc ? `${loc}: ${msg}` : msg;
          }
          return String(err);
        })
        .join("; ");
    }
  }

  return "Ocurrió un error inesperado. Intenta de nuevo.";
}
