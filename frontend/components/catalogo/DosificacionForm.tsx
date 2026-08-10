"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { useListarDiasMenuApiV1PlanificacionMenusQuincenalesMenuIdDiasGet } from "@/lib/api/generated/endpoints/planificación-menús/planificación-menús";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { MenuQuincenalOut } from "@/lib/api/generated/model/menuQuincenalOut";

const TIPO_SERVICIO_LABEL: Record<string, string> = {
  DESAYUNO: "Desayuno",
  ALMUERZO: "Almuerzo",
  CENA: "Cena",
};

export function DosificacionForm({
  menus,
  centros,
}: {
  menus: MenuQuincenalOut[];
  centros: CentroConsumoOut[];
}) {
  const router = useRouter();

  const [menuId, setMenuId] = useState<number | string>(menus[0]?.menu_id ?? "");
  // Selección explícita del usuario para el día; si está vacía, o si ya no
  // pertenece al menú actual (cambió de menú), se usa el primer día de la
  // lista — calculado en cada render, sin useEffect (evita el
  // "cascading render" de sincronizar un estado derivado de otro).
  const [menuDiaIdOverride, setMenuDiaIdOverride] = useState<number | string>("");
  const [centroConsumoId, setCentroConsumoId] = useState<number | string>(
    centros[0]?.centro_consumo_id ?? "",
  );

  const { data: dias, isFetching: cargandoDias } =
    useListarDiasMenuApiV1PlanificacionMenusQuincenalesMenuIdDiasGet(Number(menuId), {
      query: { enabled: menuId !== "" },
    });

  const diasDelMenu = useMemo(
    () => (Array.isArray(dias?.data) ? dias.data : []),
    [dias],
  );

  const menuDiaId = diasDelMenu.some((dia) => dia.menu_dia_id === Number(menuDiaIdOverride))
    ? menuDiaIdOverride
    : (diasDelMenu[0]?.menu_dia_id ?? "");

  function handleMenuChange(value: string) {
    setMenuId(value);
    setMenuDiaIdOverride("");
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!menuDiaId || !centroConsumoId) return;
    const params = new URLSearchParams();
    params.set("menu_dia_id", String(menuDiaId));
    params.set("centro_consumo_id", String(centroConsumoId));
    router.push(`/dosificacion/calcular?${params.toString()}`);
  }

  if (menus.length === 0 || centros.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un menú quincenal (con días) y un centro de
        consumo para calcular una dosificación.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
      <div className="space-y-1">
        <label htmlFor="menu_id" className="text-sm font-medium">
          Menú quincenal
        </label>
        <select
          id="menu_id"
          value={menuId}
          onChange={(event) => handleMenuChange(event.target.value)}
          required
          className="w-56 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {menus.map((menu) => (
            <option key={menu.menu_id} value={menu.menu_id}>
              {menu.quincena_inicio} — {menu.quincena_fin} ({menu.estado})
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1">
        <label htmlFor="menu_dia_id" className="text-sm font-medium">
          Día de menú
        </label>
        <select
          id="menu_dia_id"
          value={menuDiaId}
          onChange={(event) => setMenuDiaIdOverride(event.target.value)}
          required
          disabled={cargandoDias || diasDelMenu.length === 0}
          className="w-64 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:opacity-60"
        >
          {cargandoDias && <option value="">Cargando días…</option>}
          {!cargandoDias && diasDelMenu.length === 0 && (
            <option value="">Este menú todavía no tiene días</option>
          )}
          {diasDelMenu.map((dia) => (
            <option key={dia.menu_dia_id} value={dia.menu_dia_id}>
              {dia.fecha} — {TIPO_SERVICIO_LABEL[dia.tipo_servicio] ?? dia.tipo_servicio} (
              {dia.raciones_programadas} raciones)
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
          className="w-56 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {centros.map((centro) => (
            <option key={centro.centro_consumo_id} value={centro.centro_consumo_id}>
              {centro.nombre}
            </option>
          ))}
        </select>
      </div>

      <button
        type="submit"
        disabled={!menuDiaId || !centroConsumoId}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        Ver
      </button>
    </form>
  );
}
