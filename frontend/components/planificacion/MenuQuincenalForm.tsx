"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearMenuQuincenalApiV1PlanificacionMenusQuincenalesPost } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";
import type { RacionAnualOut } from "@/lib/api/generated/model/racionAnualOut";

export function MenuQuincenalForm({ raciones }: { raciones: RacionAnualOut[] }) {
  const router = useRouter();
  const crear = useCrearMenuQuincenalApiV1PlanificacionMenusQuincenalesPost();

  const [racionAnualId, setRacionAnualId] = useState<number | string>(
    raciones[0]?.racion_anual_id ?? "",
  );
  const [quincenaInicio, setQuincenaInicio] = useState("");
  const [quincenaFin, setQuincenaFin] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        racion_anual_id: Number(racionAnualId),
        quincena_inicio: quincenaInicio,
        quincena_fin: quincenaFin,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/planificacion/menus/${response.data.menu_id}`);
    router.refresh();
  }

  if (raciones.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una ración anual para crear un menú quincenal.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="racion_anual_id" className="text-sm font-medium">
          Ración anual
        </label>
        <select
          id="racion_anual_id"
          value={racionAnualId}
          onChange={(event) => setRacionAnualId(event.target.value)}
          required
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {raciones.map((racion) => (
            <option key={racion.racion_anual_id} value={racion.racion_anual_id}>
              {racion.anio} — #{racion.racion_anual_id} ({racion.estado})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="quincena_inicio" className="text-sm font-medium">
            Quincena — inicio
          </label>
          <input
            id="quincena_inicio"
            type="date"
            value={quincenaInicio}
            onChange={(event) => setQuincenaInicio(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="quincena_fin" className="text-sm font-medium">
            Quincena — fin
          </label>
          <input
            id="quincena_fin"
            type="date"
            value={quincenaFin}
            onChange={(event) => setQuincenaFin(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Creando..." : "Crear menú quincenal"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/planificacion/menus")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
