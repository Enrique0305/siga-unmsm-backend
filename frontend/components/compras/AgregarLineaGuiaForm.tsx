"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useAgregarDetalleGuiaApiV1GuiasRemisionGuiaRemisionIdDetallePost } from "@/lib/api/generated/endpoints/guías-de-remisión/guías-de-remisión";
import type { OrdenCompraDetalleOut } from "@/lib/api/generated/model/ordenCompraDetalleOut";

export function AgregarLineaGuiaForm({
  guiaRemisionId,
  lineasOc,
}: {
  guiaRemisionId: number;
  lineasOc: OrdenCompraDetalleOut[];
}) {
  const router = useRouter();
  const agregar = useAgregarDetalleGuiaApiV1GuiasRemisionGuiaRemisionIdDetallePost();

  const [ordenCompraDetalleId, setOrdenCompraDetalleId] = useState<number | string>(
    lineasOc[0]?.orden_compra_detalle_id ?? "",
  );
  const [cantidadEntregada, setCantidadEntregada] = useState("");
  const [lote, setLote] = useState("");
  const [fechaVencimiento, setFechaVencimiento] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await agregar.mutateAsync({
      guiaRemisionId,
      data: {
        orden_compra_detalle_id: Number(ordenCompraDetalleId),
        cantidad_entregada: Number(cantidadEntregada),
        lote: lote || null,
        fecha_vencimiento: fechaVencimiento || null,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setCantidadEntregada("");
    setLote("");
    setFechaVencimiento("");
    router.refresh();
  }

  if (lineasOc.length === 0) {
    return null;
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-5 sm:items-end">
        <div className="space-y-1 sm:col-span-2">
          <label className="text-sm font-medium">Línea de OC</label>
          <select
            value={ordenCompraDetalleId}
            onChange={(event) => setOrdenCompraDetalleId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {lineasOc.map((linea) => (
              <option key={linea.orden_compra_detalle_id} value={linea.orden_compra_detalle_id}>
                {linea.producto_codigo} — {linea.producto_nombre} (saldo: {linea.saldo_oc})
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Cant. entregada</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={cantidadEntregada}
            onChange={(event) => setCantidadEntregada(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Lote (opcional)</label>
          <input
            value={lote}
            onChange={(event) => setLote(event.target.value)}
            maxLength={60}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Vencimiento (opcional)</label>
          <input
            type="date"
            value={fechaVencimiento}
            onChange={(event) => setFechaVencimiento(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={agregar.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {agregar.isPending ? "Agregando..." : "Agregar línea"}
      </button>
    </form>
  );
}
