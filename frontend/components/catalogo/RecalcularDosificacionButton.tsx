"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCalcularDosificacionApiV1PlanificacionDiasMenuDiaIdDosificacionPost } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";

export function RecalcularDosificacionButton({
  menuDiaId,
  centroConsumoId,
}: {
  menuDiaId: number;
  centroConsumoId: number;
}) {
  const router = useRouter();
  const calcular = useCalcularDosificacionApiV1PlanificacionDiasMenuDiaIdDosificacionPost();
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);
    const response = await calcular.mutateAsync({
      menuDiaId,
      params: { centro_consumo_id: centroConsumoId },
    });
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
      <button
        type="button"
        onClick={handleClick}
        disabled={calcular.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {calcular.isPending ? "Calculando..." : "Calcular / recalcular dosificación"}
      </button>
    </div>
  );
}
