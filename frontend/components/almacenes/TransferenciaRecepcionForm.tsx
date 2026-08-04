"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useRecibirTransferenciaApiV1TransferenciasTransferenciaIdRecepcionPost } from "@/lib/api/generated/endpoints/transferencias-entre-almacenes/transferencias-entre-almacenes";
import type { TransferenciaAlmacenDetalleOut } from "@/lib/api/generated/model/transferenciaAlmacenDetalleOut";
import type { TransferenciaRecepcionDetalleIn } from "@/lib/api/generated/model/transferenciaRecepcionDetalleIn";

export function TransferenciaRecepcionForm({
  transferenciaId,
  lineas,
}: {
  transferenciaId: number;
  lineas: TransferenciaAlmacenDetalleOut[];
}) {
  const router = useRouter();
  const recibir = useRecibirTransferenciaApiV1TransferenciasTransferenciaIdRecepcionPost();

  const [detalle, setDetalle] = useState<TransferenciaRecepcionDetalleIn[]>(() =>
    lineas.map((linea) => ({
      transferencia_detalle_id: linea.transferencia_detalle_id,
      cantidad_recibida: linea.cantidad_enviada,
      observacion_diferencia: null,
    })),
  );
  const [error, setError] = useState<string | null>(null);

  function actualizarLinea(index: number, patch: Partial<TransferenciaRecepcionDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await recibir.mutateAsync({
      transferenciaId,
      data: { detalle },
    });

    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <p className="text-sm font-medium text-foreground">
        Confirmar recepción (todas las líneas juntas)
      </p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      {detalle.map((fila, index) => {
        const linea = lineas.find((l) => l.transferencia_detalle_id === fila.transferencia_detalle_id);
        return (
          <div
            key={fila.transferencia_detalle_id}
            className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-4 sm:items-end"
          >
            <div className="sm:col-span-2">
              <p className="text-xs text-text-secondary">Producto</p>
              <p className="text-sm">
                {linea?.producto_codigo} — {linea?.producto_nombre}
              </p>
              <p className="text-xs text-text-secondary">Enviada: {linea?.cantidad_enviada}</p>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Cant. recibida</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={fila.cantidad_recibida}
                onChange={(event) =>
                  actualizarLinea(index, { cantidad_recibida: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Observación (opcional)</label>
              <input
                value={fila.observacion_diferencia ?? ""}
                onChange={(event) =>
                  actualizarLinea(index, { observacion_diferencia: event.target.value || null })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
          </div>
        );
      })}
      <button
        type="submit"
        disabled={recibir.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {recibir.isPending ? "Confirmando..." : "Confirmar recepción"}
      </button>
    </form>
  );
}
