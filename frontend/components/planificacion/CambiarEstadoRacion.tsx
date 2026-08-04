"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCambiarEstadoRacionAnualApiV1PlanificacionRacionesAnualesRacionAnualIdEstadoPatch } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";

/** Espejo de crud/planificacion.py::TRANSICIONES_VALIDAS_RACION — solo UX. */
const TRANSICIONES_VALIDAS: Record<string, string[]> = {
  BORRADOR: ["APROBADO"],
  APROBADO: [],
};

export function CambiarEstadoRacion({
  racionAnualId,
  estadoActual,
}: {
  racionAnualId: number;
  estadoActual: string;
}) {
  const router = useRouter();
  const cambiarEstado =
    useCambiarEstadoRacionAnualApiV1PlanificacionRacionesAnualesRacionAnualIdEstadoPatch();
  const [error, setError] = useState<string | null>(null);

  const opciones = TRANSICIONES_VALIDAS[estadoActual] ?? [];

  async function handleClick(estado: string) {
    setError(null);
    const response = await cambiarEstado.mutateAsync({ racionAnualId, data: { estado } });
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
