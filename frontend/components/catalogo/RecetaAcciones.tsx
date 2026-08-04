"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import {
  useNuevaVersionRecetaApiV1RecetasRecetaIdVersionesPost,
  useRecalcularNutricionApiV1RecetasRecetaIdRecalcularNutricionPost,
} from "@/lib/api/generated/endpoints/recetas/recetas";

export function RecetaAcciones({ recetaId }: { recetaId: number }) {
  const router = useRouter();
  const nuevaVersion = useNuevaVersionRecetaApiV1RecetasRecetaIdVersionesPost();
  const recalcular = useRecalcularNutricionApiV1RecetasRecetaIdRecalcularNutricionPost();
  const [error, setError] = useState<string | null>(null);

  async function handleNuevaVersion() {
    setError(null);
    const response = await nuevaVersion.mutateAsync({ recetaId });
    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }
    router.push(`/dosificacion/recetas/${response.data.receta_id}`);
    router.refresh();
  }

  async function handleRecalcular() {
    setError(null);
    const response = await recalcular.mutateAsync({ recetaId });
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
          onClick={handleNuevaVersion}
          disabled={nuevaVersion.isPending}
          className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground hover:bg-surface disabled:opacity-60"
        >
          {nuevaVersion.isPending ? "Creando versión..." : "Crear nueva versión"}
        </button>
        <button
          type="button"
          onClick={handleRecalcular}
          disabled={recalcular.isPending}
          className="rounded-md border border-border/30 px-3 py-1.5 text-sm text-foreground hover:bg-surface disabled:opacity-60"
        >
          {recalcular.isPending ? "Recalculando..." : "Recalcular nutrición"}
        </button>
      </div>
    </div>
  );
}
