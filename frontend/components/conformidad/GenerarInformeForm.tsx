"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useGenerarInformeApiV1InformesConformidadPagoPost } from "@/lib/api/generated/endpoints/informes-de-conformidad-para-pago/informes-de-conformidad-para-pago";

export function GenerarInformeForm({ ordenCompraId }: { ordenCompraId: number }) {
  const router = useRouter();
  const generar = useGenerarInformeApiV1InformesConformidadPagoPost();

  const [numeroInforme, setNumeroInforme] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await generar.mutateAsync({
      data: { numero_informe: numeroInforme, orden_compra_id: ordenCompraId },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/conformidad/${response.data.informe_id}`);
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
      {error && (
        <p className="w-full rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="space-y-1">
        <label className="text-xs text-text-secondary">N° de informe</label>
        <input
          value={numeroInforme}
          onChange={(event) => setNumeroInforme(event.target.value)}
          required
          maxLength={40}
          className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={generar.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {generar.isPending ? "Generando..." : "Generar informe de conformidad"}
      </button>
    </form>
  );
}
