import { notFound } from "next/navigation";

import { CambiarEstadoRequerimiento } from "@/components/planificacion/CambiarEstadoRequerimiento";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { RequerimientoAnualDetailOut } from "@/lib/api/generated/model/requerimientoAnualDetailOut";

const ROLES_EDICION = ["ADMIN", "NUTRICION", "LOGISTICA_CENTRAL"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral"> = {
  BORRADOR: "neutral",
  EN_REVISION: "warning",
  APROBADO: "warning",
  VIGENTE: "success",
};

export default async function RequerimientoDetailPage({
  params,
}: PageProps<"/planificacion/requerimientos/[id]">) {
  const { id } = await params;

  let requerimiento: RequerimientoAnualDetailOut;
  try {
    requerimiento = await serverFetch<RequerimientoAnualDetailOut>(`/requerimientos-anuales/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const session = await getSession();
  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              Requerimiento anual — Ración #{requerimiento.racion_anual_id}
            </h2>
            <p className="text-sm text-text-secondary">
              v{requerimiento.version}
              {requerimiento.aprobado_en && ` · aprobado el ${requerimiento.aprobado_en.slice(0, 10)}`}
            </p>
          </div>
          <Badge
            label={requerimiento.estado}
            variant={ESTADO_VARIANT[requerimiento.estado] ?? "neutral"}
          />
        </div>

        {requerimiento.presupuesto_referencial_total != null && (
          <p className="mt-4 text-sm">
            Presupuesto referencial total: S/{" "}
            {requerimiento.presupuesto_referencial_total.toLocaleString("es-PE", {
              minimumFractionDigits: 2,
            })}
          </p>
        )}

        {puedeEditar && (
          <div className="mt-4">
            <CambiarEstadoRequerimiento
              requerimientoAnualId={requerimiento.requerimiento_anual_id}
              estadoActual={requerimiento.estado}
            />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Detalle</h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Cantidad estimada anual</th>
              <th className="py-2 font-medium">Presupuesto referencial</th>
            </tr>
          </thead>
          <tbody>
            {requerimiento.detalle.map((linea) => (
              <tr
                key={linea.requerimiento_detalle_id}
                className="border-b border-border/10 last:border-0"
              >
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_estimada_anual}</td>
                <td className="py-2">
                  {linea.presupuesto_referencial != null
                    ? `S/ ${linea.presupuesto_referencial.toLocaleString("es-PE", { minimumFractionDigits: 2 })}`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
