import { notFound } from "next/navigation";

import { Badge } from "@/components/ui/Badge";
import { CrearActaForm } from "@/components/recepcion/CrearActaForm";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { GuiaRemisionListOut } from "@/lib/api/generated/model/guiaRemisionListOut";
import type { InspeccionDetailOut } from "@/lib/api/generated/model/inspeccionDetailOut";

const ROLES_EDICION = ["ADMIN", "INSPECTOR"];

const RESULTADO_VARIANT: Record<string, "success" | "danger" | "neutral"> = {
  CONFORME: "success",
  OBSERVADO: "danger",
};

export default async function InspeccionDetailPage({
  params,
}: PageProps<"/recepcion/[id]">) {
  const { id } = await params;

  let inspeccion: InspeccionDetailOut;
  try {
    inspeccion = await serverFetch<InspeccionDetailOut>(`/inspecciones/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, guia] = await Promise.all([
    getSession(),
    serverFetch<GuiaRemisionListOut>(`/guias-remision/${inspeccion.guia_remision_id}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h2 className="text-lg font-semibold text-foreground">
          Inspección #{inspeccion.inspeccion_id}
        </h2>
        <p className="mt-1 text-sm text-text-secondary">
          Guía {guia.numero_guia} · {guia.proveedor_razon_social} · Destino{" "}
          {guia.almacen_destino_codigo} — {guia.almacen_destino_nombre}
        </p>
        <p className="mt-1 text-sm text-text-secondary">
          Fecha de inspección: {inspeccion.fecha_inspeccion}
        </p>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas inspeccionadas</h3>
        <div className="space-y-3">
          {inspeccion.detalle.map((linea) => (
            <div key={linea.inspeccion_detalle_id} className="rounded-md border border-border/20 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </p>
                <Badge
                  label={linea.resultado}
                  variant={RESULTADO_VARIANT[linea.resultado] ?? "neutral"}
                />
              </div>
              <dl className="mt-2 grid grid-cols-2 gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-text-secondary">Conforme</dt>
                  <dd>{linea.cantidad_conforme}</dd>
                </div>
                <div>
                  <dt className="text-xs text-text-secondary">Observada</dt>
                  <dd>{linea.cantidad_observada}</dd>
                </div>
              </dl>
              {puedeEditar && linea.resultado === "OBSERVADO" && (
                <CrearActaForm inspeccionDetalleId={linea.inspeccion_detalle_id} />
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
