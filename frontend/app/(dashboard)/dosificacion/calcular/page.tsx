import { DosificacionForm } from "@/components/catalogo/DosificacionForm";
import { RecalcularDosificacionButton } from "@/components/catalogo/RecalcularDosificacionButton";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { DosificacionDetalleOut } from "@/lib/api/generated/model/dosificacionDetalleOut";
import type { MenuDiaOut } from "@/lib/api/generated/model/menuDiaOut";
import type { PageMenuQuincenalOut } from "@/lib/api/generated/model/pageMenuQuincenalOut";

const ROLES_CALCULO = ["ADMIN", "NUTRICION", "LOGISTICA_CENTRAL"];

const TIPO_SERVICIO_LABEL: Record<string, string> = {
  DESAYUNO: "Desayuno",
  ALMUERZO: "Almuerzo",
  CENA: "Cena",
};

export default async function CalcularDosificacionPage({
  searchParams,
}: PageProps<"/dosificacion/calcular">) {
  const params = await searchParams;
  const menuDiaIdRaw = typeof params.menu_dia_id === "string" ? params.menu_dia_id : "";
  const centroConsumoIdRaw =
    typeof params.centro_consumo_id === "string" ? params.centro_consumo_id : "";

  const menuDiaId = Number(menuDiaIdRaw) || null;
  const centroConsumoId = Number(centroConsumoIdRaw) || null;

  const [session, menusPage, centros, detalle, dia] = await Promise.all([
    getSession(),
    serverFetch<PageMenuQuincenalOut>("/planificacion/menus-quincenales?page_size=100"),
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
    menuDiaId
      ? serverFetch<DosificacionDetalleOut[]>(`/planificacion/dias/${menuDiaId}/dosificacion`)
      : Promise.resolve(null),
    menuDiaId
      ? serverFetch<MenuDiaOut>(`/planificacion/dias/${menuDiaId}`)
      : Promise.resolve(null),
  ]);

  const puedeCalcular = session ? ROLES_CALCULO.includes(session.rol) : false;
  const centro = centros.find((c) => c.centro_consumo_id === centroConsumoId) ?? null;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-border/20 bg-white p-4">
        <DosificacionForm menus={menusPage.items} centros={centros} />
      </div>

      {menuDiaId && centroConsumoId && (
        <div className="space-y-3 rounded-lg border border-border/20 bg-white p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">
              {dia
                ? `${dia.fecha} — ${TIPO_SERVICIO_LABEL[dia.tipo_servicio] ?? dia.tipo_servicio}`
                : `Día de menú #${menuDiaId}`}
              {" · "}
              {centro?.nombre ?? `Centro de consumo #${centroConsumoId}`}
            </h3>
            {puedeCalcular && (
              <RecalcularDosificacionButton
                menuDiaId={menuDiaId}
                centroConsumoId={centroConsumoId}
              />
            )}
          </div>

          {detalle && detalle.length > 0 ? (
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border/20 text-text-secondary">
                <tr>
                  <th className="py-2 font-medium">Alimento</th>
                  <th className="py-2 font-medium">Raciones</th>
                  <th className="py-2 font-medium">Cant. bruta</th>
                  <th className="py-2 font-medium">Cant. neta</th>
                </tr>
              </thead>
              <tbody>
                {detalle.map((fila) => (
                  <tr key={fila.dosificacion_id} className="border-b border-border/10 last:border-0">
                    <td className="py-2">
                      {fila.alimento_codigo} — {fila.alimento_nombre}
                    </td>
                    <td className="py-2">{fila.raciones_programadas}</td>
                    <td className="py-2">{fila.cantidad_bruta_requerida} g</td>
                    <td className="py-2">{fila.cantidad_neta_requerida} g</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-text-secondary">
              Sin dosificación calculada todavía para este día de menú.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
