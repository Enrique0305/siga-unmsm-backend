"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCambiarEstadoSolicitudApiV1SolicitudesCocinaSolicitudCocinaIdEstadoPatch } from "@/lib/api/generated/endpoints/solicitudes-de-cocina/solicitudes-de-cocina";

export function AnularSolicitudButton({ solicitudCocinaId }: { solicitudCocinaId: number }) {
  const router = useRouter();
  const anular = useCambiarEstadoSolicitudApiV1SolicitudesCocinaSolicitudCocinaIdEstadoPatch();
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setError(null);
    const response = await anular.mutateAsync({
      solicitudCocinaId,
      data: { estado: "ANULADA" },
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
        disabled={anular.isPending}
        className="rounded-md border border-danger/30 px-4 py-2 text-sm font-medium text-danger hover:bg-danger/10 disabled:opacity-60"
      >
        {anular.isPending ? "Anulando..." : "Anular solicitud"}
      </button>
    </div>
  );
}
