"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

export function DosificacionForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [menuDiaId, setMenuDiaId] = useState(searchParams.get("menu_dia_id") ?? "");
  const [centroConsumoId, setCentroConsumoId] = useState(
    searchParams.get("centro_consumo_id") ?? "",
  );

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams();
    params.set("menu_dia_id", menuDiaId);
    params.set("centro_consumo_id", centroConsumoId);
    router.push(`/dosificacion/calcular?${params.toString()}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <label htmlFor="menu_dia_id" className="text-sm font-medium">
          ID de día de menú
        </label>
        <input
          id="menu_dia_id"
          type="number"
          min="1"
          value={menuDiaId}
          onChange={(event) => setMenuDiaId(event.target.value)}
          required
          className="w-40 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="centro_consumo_id" className="text-sm font-medium">
          ID de centro de consumo
        </label>
        <input
          id="centro_consumo_id"
          type="number"
          min="1"
          value={centroConsumoId}
          onChange={(event) => setCentroConsumoId(event.target.value)}
          required
          className="w-40 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>
      <button
        type="submit"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
      >
        Ver
      </button>
    </form>
  );
}
