"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearRacionAnualApiV1PlanificacionRacionesAnualesPost } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

export function RacionAnualForm({
  sedes,
  centros,
}: {
  sedes: SedeOut[];
  centros: CentroConsumoOut[];
}) {
  const router = useRouter();
  const crear = useCrearRacionAnualApiV1PlanificacionRacionesAnualesPost();

  const [sedeId, setSedeId] = useState<number | string>(sedes[0]?.sede_id ?? "");
  const centrosDeLaSede = useMemo(
    () => centros.filter((centro) => centro.sede_id === Number(sedeId)),
    [centros, sedeId],
  );
  const [centroConsumoId, setCentroConsumoId] = useState<number | string>(
    centrosDeLaSede[0]?.centro_consumo_id ?? "",
  );
  const [anio, setAnio] = useState(String(new Date().getFullYear()));
  const [poblacionAtendida, setPoblacionAtendida] = useState("");
  const [racionesDia, setRacionesDia] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSedeChange(value: string) {
    setSedeId(value);
    const opciones = centros.filter((centro) => centro.sede_id === Number(value));
    setCentroConsumoId(opciones[0]?.centro_consumo_id ?? "");
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        sede_id: Number(sedeId),
        centro_consumo_id: Number(centroConsumoId),
        anio: Number(anio),
        poblacion_atendida: Number(poblacionAtendida),
        raciones_dia: Number(racionesDia),
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/planificacion/${response.data.racion_anual_id}`);
    router.refresh();
  }

  if (sedes.length === 0 || centros.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una sede y un centro de consumo para crear una
        ración anual.
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="sede_id" className="text-sm font-medium">
            Sede
          </label>
          <select
            id="sede_id"
            value={sedeId}
            onChange={(event) => handleSedeChange(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {sedes.map((sede) => (
              <option key={sede.sede_id} value={sede.sede_id}>
                {sede.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="centro_consumo_id" className="text-sm font-medium">
            Centro de consumo
          </label>
          <select
            id="centro_consumo_id"
            value={centroConsumoId}
            onChange={(event) => setCentroConsumoId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {centrosDeLaSede.length === 0 && <option value="">Sin centros en esta sede</option>}
            {centrosDeLaSede.map((centro) => (
              <option key={centro.centro_consumo_id} value={centro.centro_consumo_id}>
                {centro.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <label htmlFor="anio" className="text-sm font-medium">
            Año
          </label>
          <input
            id="anio"
            type="number"
            min="2020"
            max="2100"
            value={anio}
            onChange={(event) => setAnio(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="poblacion_atendida" className="text-sm font-medium">
            Población atendida
          </label>
          <input
            id="poblacion_atendida"
            type="number"
            min="1"
            value={poblacionAtendida}
            onChange={(event) => setPoblacionAtendida(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="raciones_dia" className="text-sm font-medium">
            Raciones/día
          </label>
          <input
            id="raciones_dia"
            type="number"
            min="1"
            value={racionesDia}
            onChange={(event) => setRacionesDia(event.target.value)}
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
          {crear.isPending ? "Creando..." : "Crear ración anual"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/planificacion")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
