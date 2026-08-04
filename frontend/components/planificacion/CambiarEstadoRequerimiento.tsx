"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCambiarEstadoRequerimientoApiV1RequerimientosAnualesRequerimientoAnualIdEstadoPatch } from "@/lib/api/generated/endpoints/requerimiento-anual-de-insumos/requerimiento-anual-de-insumos";

/** Espejo de crud/requerimiento.py::TRANSICIONES_VALIDAS — solo UX. */
const TRANSICIONES_VALIDAS: Record<string, string[]> = {
  BORRADOR: ["EN_REVISION"],
  EN_REVISION: ["APROBADO", "BORRADOR"],
  APROBADO: ["VIGENTE"],
  VIGENTE: [],
};

export function CambiarEstadoRequerimiento({
  requerimientoAnualId,
  estadoActual,
}: {
  requerimientoAnualId: number;
  estadoActual: string;
}) {
  const router = useRouter();
  const cambiarEstado =
    useCambiarEstadoRequerimientoApiV1RequerimientosAnualesRequerimientoAnualIdEstadoPatch();
  const [error, setError] = useState<string | null>(null);

  const opciones = TRANSICIONES_VALIDAS[estadoActual] ?? [];

  async function handleClick(estado: string) {
    setError(null);
    const response = await cambiarEstado.mutateAsync({ requerimientoAnualId, data: { estado } });
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
