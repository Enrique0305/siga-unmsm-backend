"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ValorNutricionalFields } from "@/components/catalogo/ValorNutricionalFields";
import { extractErrorMessage } from "@/lib/api/errors";
import { useCorregirValoresNutricionalesApiV1AlimentosAlimentoIdVersionesPost } from "@/lib/api/generated/endpoints/catálogo-nutricional/catálogo-nutricional";
import type { ValorNutricional } from "@/lib/api/generated/model/valorNutricional";

export function CorregirValoresForm({ alimentoId }: { alimentoId: number }) {
  const router = useRouter();
  const corregir = useCorregirValoresNutricionalesApiV1AlimentosAlimentoIdVersionesPost();

  const [fuente, setFuente] = useState("");
  const [valores, setValores] = useState<ValorNutricional>({});
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await corregir.mutateAsync({
      alimentoId,
      data: { ...valores, fuente },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setFuente("");
    setValores({});
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="fuente_correccion" className="text-sm font-medium">
          Fuente de la corrección
        </label>
        <input
          id="fuente_correccion"
          value={fuente}
          onChange={(event) => setFuente(event.target.value)}
          required
          maxLength={255}
          className="w-full max-w-md rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <ValorNutricionalFields
        values={valores}
        onChange={(patch) => setValores((prev) => ({ ...prev, ...patch }))}
      />

      <button
        type="submit"
        disabled={corregir.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {corregir.isPending ? "Guardando..." : "Registrar nueva versión"}
      </button>
    </form>
  );
}
