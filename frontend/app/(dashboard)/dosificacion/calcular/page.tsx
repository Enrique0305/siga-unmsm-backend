import { DosificacionForm } from "@/components/catalogo/DosificacionForm";
import { RecalcularDosificacionButton } from "@/components/catalogo/RecalcularDosificacionButton";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { DosificacionDetalleOut } from "@/lib/api/generated/model/dosificacionDetalleOut";

const ROLES_CALCULO = ["ADMIN", "NUTRICION", "LOGISTICA_CENTRAL"];

export default async function CalcularDosificacionPage({
  searchParams,
}: PageProps<"/dosificacion/calcular">) {
  const params = await searchParams;
  const menuDiaIdRaw = typeof params.menu_dia_id === "string" ? params.menu_dia_id : "";
  const centroConsumoIdRaw =
    typeof params.centro_consumo_id === "string" ? params.centro_consumo_id : "";

  const menuDiaId = Number(menuDiaIdRaw) || null;
  const centroConsumoId = Number(centroConsumoIdRaw) || null;

  const [session, detalle] = await Promise.all([
    getSession(),
    menuDiaId
      ? serverFetch<DosificacionDetalleOut[]>(`/planificacion/dias/${menuDiaId}/dosificacion`)
      : Promise.resolve(null),
  ]);

  const puedeCalcular = session ? ROLES_CALCULO.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <p className="max-w-2xl text-xs text-text-secondary">
        El módulo 01 (Planificación de menús) todavía no está construido, así
        que no hay un selector de día de menú — se ingresa el ID
        directamente. RN-24: el cálculo es idempotente (recalcular reemplaza
        el resultado anterior, nunca duplica).
      </p>

      <div className="rounded-lg border border-border/20 bg-white p-4">
        <DosificacionForm />
      </div>

      {menuDiaId && centroConsumoId && (
        <div className="space-y-3 rounded-lg border border-border/20 bg-white p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">
              Día de menú #{menuDiaId} — Centro de consumo #{centroConsumoId}
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
                  <th className="py-2 font-medium">Almacén</th>
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
                    <td className="py-2 text-text-secondary">#{fila.almacen_id}</td>
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
