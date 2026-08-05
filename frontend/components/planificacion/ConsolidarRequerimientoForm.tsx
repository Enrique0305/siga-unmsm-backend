"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useConsolidarRequerimientoApiV1PlanificacionRacionesAnualesRacionAnualIdConsolidarRequerimientoPost } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";

export function ConsolidarRequerimientoForm({ racionAnualId }: { racionAnualId: number }) {
  const router = useRouter();
  const consolidar =
    useConsolidarRequerimientoApiV1PlanificacionRacionesAnualesRacionAnualIdConsolidarRequerimientoPost();
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await consolidar.mutateAsync({ racionAnualId });
    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/planificacion/requerimientos/${response.data.requerimiento_anual_id}`);
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <button
        type="submit"
        disabled={consolidar.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {consolidar.isPending ? "Consolidando..." : "Consolidar requerimiento desde BOM"}
      </button>
      <p className="text-xs text-text-secondary">
        Suma la dosificación (RN-24) ya calculada de todos los días de menú de esta
        ración anual y genera un requerimiento anual en BORRADOR.
      </p>
    </form>
  );
}
