"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useAutorizarExcedenteApiV1OrdenesCompraDetalleOrdenCompraDetalleIdAutorizacionesExcedentePost } from "@/lib/api/generated/endpoints/órdenes-de-compra/órdenes-de-compra";
import type { OrdenCompraDetalleOut } from "@/lib/api/generated/model/ordenCompraDetalleOut";

export function AutorizarExcedenteForm({ lineas }: { lineas: OrdenCompraDetalleOut[] }) {
  const router = useRouter();
  const autorizar =
    useAutorizarExcedenteApiV1OrdenesCompraDetalleOrdenCompraDetalleIdAutorizacionesExcedentePost();

  const [lineaId, setLineaId] = useState<number | string>(
    lineas[0]?.orden_compra_detalle_id ?? "",
  );
  const [cantidadExcedente, setCantidadExcedente] = useState("");
  const [justificacion, setJustificacion] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await autorizar.mutateAsync({
      ordenCompraDetalleId: Number(lineaId),
      data: {
        cantidad_excedente: Number(cantidadExcedente),
        justificacion,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setCantidadExcedente("");
    setJustificacion("");
    router.refresh();
  }

  if (lineas.length === 0) {
    return null;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
        <div className="space-y-1 sm:col-span-2">
          <label className="text-sm font-medium">Línea de OC</label>
          <select
            value={lineaId}
            onChange={(event) => setLineaId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {lineas.map((linea) => (
              <option key={linea.orden_compra_detalle_id} value={linea.orden_compra_detalle_id}>
                {linea.producto_codigo} — {linea.producto_nombre} (saldo: {linea.saldo_oc})
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Cantidad excedente</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={cantidadExcedente}
            onChange={(event) => setCantidadExcedente(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={autorizar.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {autorizar.isPending ? "Autorizando..." : "Autorizar"}
        </button>
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium">Justificación</label>
        <input
          value={justificacion}
          onChange={(event) => setJustificacion(event.target.value)}
          required
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>
    </form>
  );
}
