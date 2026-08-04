"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearPenalidadApiV1PenalidadesPost } from "@/lib/api/generated/endpoints/penalidades/penalidades";
import type { OrdenCompraOut } from "@/lib/api/generated/model/ordenCompraOut";

export function PenalidadForm({ ordenesCompra }: { ordenesCompra: OrdenCompraOut[] }) {
  const router = useRouter();
  const crear = useCrearPenalidadApiV1PenalidadesPost();

  const [ordenCompraId, setOrdenCompraId] = useState<number | string>(
    ordenesCompra[0]?.orden_compra_id ?? "",
  );
  const [montoPenalidad, setMontoPenalidad] = useState("");
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        orden_compra_id: Number(ordenCompraId),
        monto_penalidad: Number(montoPenalidad),
        motivo,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push("/conformidad/penalidades");
    router.refresh();
  }

  if (ordenesCompra.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una orden de compra para registrar una penalidad.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="orden_compra_id" className="text-sm font-medium">
          Orden de compra
        </label>
        <select
          id="orden_compra_id"
          value={ordenCompraId}
          onChange={(event) => setOrdenCompraId(event.target.value)}
          required
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {ordenesCompra.map((oc) => (
            <option key={oc.orden_compra_id} value={oc.orden_compra_id}>
              {oc.numero_oc} ({oc.estado})
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label htmlFor="monto_penalidad" className="text-sm font-medium">
          Monto de la penalidad
        </label>
        <input
          id="monto_penalidad"
          type="number"
          min="0.01"
          step="0.01"
          value={montoPenalidad}
          onChange={(event) => setMontoPenalidad(event.target.value)}
          required
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="motivo" className="text-sm font-medium">
          Motivo
        </label>
        <input
          id="motivo"
          value={motivo}
          onChange={(event) => setMotivo(event.target.value)}
          required
          maxLength={255}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Registrando..." : "Registrar penalidad"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/conformidad/penalidades")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
