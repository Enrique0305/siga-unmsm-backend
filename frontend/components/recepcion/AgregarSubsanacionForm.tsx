"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearSubsanacionApiV1ActasObservacionActaObservacionIdSubsanacionesPost } from "@/lib/api/generated/endpoints/actas-de-observación/actas-de-observación";

export function AgregarSubsanacionForm({ actaObservacionId }: { actaObservacionId: number }) {
  const router = useRouter();
  const crear = useCrearSubsanacionApiV1ActasObservacionActaObservacionIdSubsanacionesPost();

  const [fechaPresentacion, setFechaPresentacion] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      actaObservacionId,
      data: { fecha_presentacion: fechaPresentacion, descripcion: descripcion || null },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setFechaPresentacion("");
    setDescripcion("");
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-md border border-border/20 p-3">
      <p className="text-xs font-medium text-foreground">Agregar subsanación</p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:items-end">
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Fecha de presentación</label>
          <input
            type="date"
            value={fechaPresentacion}
            onChange={(event) => setFechaPresentacion(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1 sm:col-span-2">
          <label className="text-xs text-text-secondary">Descripción (opcional)</label>
          <input
            value={descripcion}
            onChange={(event) => setDescripcion(event.target.value)}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={crear.isPending}
        className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {crear.isPending ? "Agregando..." : "Agregar subsanación"}
      </button>
    </form>
  );
}
