"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCambiarEstadoOrdenCompraApiV1OrdenesCompraOrdenCompraIdEstadoPatch } from "@/lib/api/generated/endpoints/órdenes-de-compra/órdenes-de-compra";

/**
 * crud/orden_compra.py::TRANSICIONES_VALIDAS permite EMITIDA->{ANULADA,
 * CERRADO,PENALIZADO}, pero PENALIZADO es un efecto secundario que decide
 * el Módulo 5 al procesar CERRADO (no una acción directa de usuario) —
 * por eso acá solo se exponen ANULADA y CERRADO.
 */
export function CambiarEstadoOC({
  ordenCompraId,
  estadoActual,
}: {
  ordenCompraId: number;
  estadoActual: string;
}) {
  const router = useRouter();
  const cambiarEstado = useCambiarEstadoOrdenCompraApiV1OrdenesCompraOrdenCompraIdEstadoPatch();
  const [error, setError] = useState<string | null>(null);

  if (estadoActual !== "EMITIDA") {
    return null;
  }

  async function handleClick(estado: string) {
    setError(null);
    const response = await cambiarEstado.mutateAsync({ ordenCompraId, data: { estado } });
    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }
    router.refresh();
  }

  return (
    <div className="space-y-2">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => handleClick("ANULADA")}
          disabled={cambiarEstado.isPending}
          className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground hover:bg-surface disabled:opacity-60"
        >
          Anular
        </button>
        <button
          type="button"
          onClick={() => handleClick("CERRADO")}
          disabled={cambiarEstado.isPending}
          className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground hover:bg-surface disabled:opacity-60"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}
