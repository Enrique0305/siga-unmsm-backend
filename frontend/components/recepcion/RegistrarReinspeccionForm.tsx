"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useRegistrarReinspeccionApiV1ActasObservacionSubsanacionesSubsanacionIdReinspeccionPatch } from "@/lib/api/generated/endpoints/actas-de-observación/actas-de-observación";

export function RegistrarReinspeccionForm({ subsanacionId }: { subsanacionId: number }) {
  const router = useRouter();
  const registrar =
    useRegistrarReinspeccionApiV1ActasObservacionSubsanacionesSubsanacionIdReinspeccionPatch();

  const [resultado, setResultado] = useState("CONFORME");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await registrar.mutateAsync({
      subsanacionId,
      data: { resultado_reinspeccion: resultado },
    });

    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex flex-wrap items-end gap-2">
      {error && (
        <p className="w-full rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="space-y-1">
        <label className="text-xs text-text-secondary">Resultado de la reinspección</label>
        <select
          value={resultado}
          onChange={(event) => setResultado(event.target.value)}
          className="rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
        >
          <option value="CONFORME">Conforme</option>
          <option value="NO_CONFORME">No conforme</option>
        </select>
      </div>
      <button
        type="submit"
        disabled={registrar.isPending}
        className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {registrar.isPending ? "Registrando..." : "Registrar reinspección"}
      </button>
    </form>
  );
}
