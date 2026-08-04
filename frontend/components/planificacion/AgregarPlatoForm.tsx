"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useAgregarPlatoADiaApiV1PlanificacionDiasMenuDiaIdPlatosPost } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";
import type { RecetaOut } from "@/lib/api/generated/model/recetaOut";

export function AgregarPlatoForm({
  menuDiaId,
  recetas,
}: {
  menuDiaId: number;
  recetas: RecetaOut[];
}) {
  const router = useRouter();
  const agregar = useAgregarPlatoADiaApiV1PlanificacionDiasMenuDiaIdPlatosPost();

  const [recetaId, setRecetaId] = useState<number | string>(recetas[0]?.receta_id ?? "");
  const [racionesOverride, setRacionesOverride] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await agregar.mutateAsync({
      menuDiaId,
      data: {
        receta_id: Number(recetaId),
        raciones_override: racionesOverride ? Number(racionesOverride) : null,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setRacionesOverride("");
    router.refresh();
  }

  if (recetas.length === 0) {
    return (
      <p className="text-sm text-text-secondary">
        No hay recetas en estado VIGENTE todavía — RN-22 exige que la receta
        esté VIGENTE antes de agregarla a un menú.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
        <div className="space-y-1 sm:col-span-2">
          <label className="text-sm font-medium">Receta (VIGENTE)</label>
          <select
            value={recetaId}
            onChange={(event) => setRecetaId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {recetas.map((receta) => (
              <option key={receta.receta_id} value={receta.receta_id}>
                {receta.codigo} — {receta.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Raciones (override, opcional)</label>
          <input
            type="number"
            min="1"
            value={racionesOverride}
            onChange={(event) => setRacionesOverride(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={agregar.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {agregar.isPending ? "Agregando..." : "Agregar plato"}
        </button>
      </div>
    </form>
  );
}
