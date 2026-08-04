"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearActaObservacionApiV1ActasObservacionDesdeInspeccionDetalleInspeccionDetalleIdPost } from "@/lib/api/generated/endpoints/actas-de-observación/actas-de-observación";

export function CrearActaForm({ inspeccionDetalleId }: { inspeccionDetalleId: number }) {
  const router = useRouter();
  const crear =
    useCrearActaObservacionApiV1ActasObservacionDesdeInspeccionDetalleInspeccionDetalleIdPost();

  const [numeroActa, setNumeroActa] = useState("");
  const [motivo, setMotivo] = useState("");
  const [plazoSubsanacion, setPlazoSubsanacion] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      inspeccionDetalleId,
      data: { numero_acta: numeroActa, motivo, plazo_subsanacion: plazoSubsanacion },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/recepcion/actas/${response.data.acta_observacion_id}`);
    router.refresh();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-2 space-y-2 rounded-md border border-warning/30 bg-warning/5 p-3"
    >
      <p className="text-xs font-medium text-warning">Crear acta de observación</p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4 sm:items-end">
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">N° de acta</label>
          <input
            value={numeroActa}
            onChange={(event) => setNumeroActa(event.target.value)}
            required
            maxLength={40}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1 sm:col-span-2">
          <label className="text-xs text-text-secondary">Motivo</label>
          <input
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            required
            maxLength={255}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Plazo subsanación</label>
          <input
            type="date"
            value={plazoSubsanacion}
            onChange={(event) => setPlazoSubsanacion(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={crear.isPending}
        className="rounded-md bg-warning px-3 py-1.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-60"
      >
        {crear.isPending ? "Creando..." : "Crear acta"}
      </button>
    </form>
  );
}
