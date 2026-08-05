"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useUpsertParametroApiV1ParametrosSistemaPut } from "@/lib/api/generated/endpoints/parámetros-del-sistema/parámetros-del-sistema";

export function ParametroSistemaForm() {
  const router = useRouter();
  const upsert = useUpsertParametroApiV1ParametrosSistemaPut();

  const [clave, setClave] = useState("");
  const [valor, setValor] = useState("");
  const [descripcion, setDescripcion] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await upsert.mutateAsync({
      data: {
        clave,
        valor,
        descripcion: descripcion || null,
      },
    });

    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setClave("");
    setValor("");
    setDescripcion("");
    router.refresh();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-lg border border-border/20 bg-white p-4"
    >
      <p className="text-sm font-medium text-foreground">Fijar parámetro del sistema</p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:items-end">
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Clave</label>
          <input
            type="text"
            maxLength={60}
            value={clave}
            onChange={(event) => setClave(event.target.value)}
            required
            placeholder="alertas_dias_vencimiento"
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Valor</label>
          <input
            type="text"
            maxLength={255}
            value={valor}
            onChange={(event) => setValor(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Descripción (opcional)</label>
          <input
            type="text"
            maxLength={255}
            value={descripcion}
            onChange={(event) => setDescripcion(event.target.value)}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <p className="text-xs text-text-secondary">
        Si la clave ya existe, se sobreescribe su valor y descripción. El valor siempre se guarda
        como texto — cada consumidor lo interpreta según lo que necesite (ej. entero).
      </p>
      <button
        type="submit"
        disabled={upsert.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {upsert.isPending ? "Guardando..." : "Guardar parámetro"}
      </button>
    </form>
  );
}
