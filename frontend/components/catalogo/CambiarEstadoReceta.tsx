"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCambiarEstadoRecetaApiV1RecetasRecetaIdEstadoPatch } from "@/lib/api/generated/endpoints/recetas/recetas";

/**
 * Espejo de crud/receta.py::TRANSICIONES_VALIDAS — solo para UX. La
 * validación real (incluida RN-23, ≥1 ingrediente para salir de BORRADOR)
 * la hace FastAPI.
 */
const TRANSICIONES_VALIDAS: Record<string, string[]> = {
  BORRADOR: ["EN_REVISION"],
  EN_REVISION: ["APROBADO", "BORRADOR"],
  APROBADO: ["VIGENTE", "DESCONTINUADO"],
  VIGENTE: ["DESCONTINUADO"],
  DESCONTINUADO: [],
};

export function CambiarEstadoReceta({
  recetaId,
  estadoActual,
}: {
  recetaId: number;
  estadoActual: string;
}) {
  const router = useRouter();
  const cambiarEstado = useCambiarEstadoRecetaApiV1RecetasRecetaIdEstadoPatch();
  const [error, setError] = useState<string | null>(null);

  const opciones = TRANSICIONES_VALIDAS[estadoActual] ?? [];

  async function handleClick(estado: string) {
    setError(null);
    const response = await cambiarEstado.mutateAsync({ recetaId, data: { estado } });
    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }
    router.refresh();
  }

  if (opciones.length === 0) {
    return null;
  }

  return (
    <div className="space-y-2">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="flex gap-2">
        {opciones.map((estado) => (
          <button
            key={estado}
            type="button"
            onClick={() => handleClick(estado)}
            disabled={cambiarEstado.isPending}
            className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground hover:bg-surface disabled:opacity-60"
          >
            Cambiar a {estado}
          </button>
        ))}
      </div>
    </div>
  );
}
