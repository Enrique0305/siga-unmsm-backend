import { notFound } from "next/navigation";

import { AutorizarExcedenteForm } from "@/components/compras/AutorizarExcedenteForm";
import { CambiarEstadoOC } from "@/components/compras/CambiarEstadoOC";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { OrdenCompraDetailOut } from "@/lib/api/generated/model/ordenCompraDetailOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  EMITIDA: "success",
  ANULADA: "neutral",
  CERRADO: "neutral",
  PENALIZADO: "danger",
};

export default async function OrdenCompraDetailPage({
  params,
}: PageProps<"/compras/[id]">) {
  const { id } = await params;

  let oc: OrdenCompraDetailOut;
  try {
    oc = await serverFetch<OrdenCompraDetailOut>(`/ordenes-compra/${id}`);
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
            <h2 className="text-lg font-semibold text-foreground">{oc.numero_oc}</h2>
            <p className="text-sm text-text-secondary">
              Contrato {oc.numero_contrato} · Periodo {oc.periodo_mes}
            </p>
          </div>
          <Badge label={oc.estado} variant={ESTADO_VARIANT[oc.estado] ?? "neutral"} />
        </div>

        {puedeEditar && (
          <div className="mt-4">
            <CambiarEstadoOC ordenCompraId={oc.orden_compra_id} estadoActual={oc.estado} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas de detalle</h3>
        <div className="space-y-4">
          {oc.detalle.map((linea) => (
            <div key={linea.orden_compra_detalle_id} className="rounded-md border border-border/20 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-medium">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </p>
                {linea.total_excedente_autorizado > 0 && (
                  <Badge
                    label={`Excedente autorizado: ${linea.total_excedente_autorizado}`}
                    variant="warning"
                  />
                )}
              </div>
              <dl className="mt-2 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-text-secondary">Solicitada</dt>
                  <dd>{linea.cantidad_solicitada}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Precio aplicado</dt>
                  <dd>S/ {linea.precio_unitario_aplicado.toFixed(2)}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Ingresada acumulada</dt>
                  <dd>{linea.cantidad_ingresada_acumulada}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Saldo OC</dt>
                  <dd>{linea.saldo_oc}</dd>
                </div>
              </dl>
              <div className="mt-2">
                <p className="text-xs font-medium text-text-secondary">Distribución</p>
                <ul className="text-xs text-text-secondary">
                  {linea.distribucion.map((dist) => (
                    <li key={dist.orden_compra_distribucion_id}>
                      {dist.almacen_codigo} — {dist.almacen_nombre}: {dist.cantidad_distribuida}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>

      {puedeEditar && (
        <div className="rounded-lg border border-border/20 bg-white p-6">
          <h3 className="mb-3 text-sm font-semibold text-foreground">
            Autorizar excedente (RN-03)
          </h3>
          <AutorizarExcedenteForm lineas={oc.detalle} />
        </div>
      )}
    </div>
  );
}
