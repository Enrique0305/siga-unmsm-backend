"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearDiaMenuApiV1PlanificacionMenusQuincenalesMenuIdDiasPost } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";

const TIPOS_SERVICIO = ["DESAYUNO", "ALMUERZO", "CENA"];

export function AgregarDiaForm({ menuId }: { menuId: number }) {
  const router = useRouter();
  const crear = useCrearDiaMenuApiV1PlanificacionMenusQuincenalesMenuIdDiasPost();

  const [fecha, setFecha] = useState("");
  const [tipoServicio, setTipoServicio] = useState(TIPOS_SERVICIO[1]);
  const [racionesProgramadas, setRacionesProgramadas] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      menuId,
      data: {
        fecha,
        tipo_servicio: tipoServicio,
        raciones_programadas: Number(racionesProgramadas),
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setFecha("");
    setRacionesProgramadas("");
    router.refresh();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
        <div className="space-y-1">
          <label className="text-sm font-medium">Fecha</label>
          <input
            type="date"
            value={fecha}
            onChange={(event) => setFecha(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Tipo de servicio</label>
          <select
            value={tipoServicio}
            onChange={(event) => setTipoServicio(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {TIPOS_SERVICIO.map((tipo) => (
              <option key={tipo} value={tipo}>
                {tipo}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-sm font-medium">Raciones programadas</label>
          <input
            type="number"
            min="1"
            value={racionesProgramadas}
            onChange={(event) => setRacionesProgramadas(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Agregando..." : "Agregar día"}
        </button>
      </div>
    </form>
  );
}
