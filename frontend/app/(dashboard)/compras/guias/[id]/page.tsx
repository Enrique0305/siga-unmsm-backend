import { notFound } from "next/navigation";

import { AgregarLineaGuiaForm } from "@/components/compras/AgregarLineaGuiaForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { GuiaRemisionDetailOut } from "@/lib/api/generated/model/guiaRemisionDetailOut";
import type { OrdenCompraDetailOut } from "@/lib/api/generated/model/ordenCompraDetailOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL", "PROVEEDOR"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral" | "danger"> = {
  PENDIENTE: "neutral",
  PARCIAL: "warning",
  CONFORME: "success",
  OBSERVADO: "danger",
  SUBSANADO: "warning",
  CERRADO: "neutral",
  PENALIZADO: "danger",
};

export default async function GuiaRemisionDetailPage({
  params,
}: PageProps<"/compras/guias/[id]">) {
  const { id } = await params;

  let guia: GuiaRemisionDetailOut;
  try {
    guia = await serverFetch<GuiaRemisionDetailOut>(`/guias-remision/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, ordenCompra] = await Promise.all([
    getSession(),
    serverFetch<OrdenCompraDetailOut>(`/ordenes-compra/${guia.orden_compra_id}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{guia.numero_guia}</h2>
            <p className="text-sm text-text-secondary">
              {guia.proveedor_razon_social} · OC {ordenCompra.numero_oc} · Destino{" "}
              {guia.almacen_destino_codigo} — {guia.almacen_destino_nombre}
            </p>
          </div>
          <Badge label={guia.estado} variant={ESTADO_VARIANT[guia.estado] ?? "neutral"} />
        </div>
        <p className="mt-2 text-sm text-text-secondary">
          Fecha de entrega: {guia.fecha_entrega}
        </p>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas entregadas</h3>
        <table className="mb-4 w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Cantidad entregada</th>
              <th className="py-2 font-medium">Lote</th>
              <th className="py-2 font-medium">Vencimiento</th>
            </tr>
          </thead>
          <tbody>
            {guia.detalle.map((linea) => (
              <tr key={linea.guia_remision_detalle_id} className="border-b border-border/10 last:border-0">
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_entregada}</td>
                <td className="py-2 text-text-secondary">{linea.lote ?? "—"}</td>
                <td className="py-2 text-text-secondary">{linea.fecha_vencimiento ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {puedeEditar && <AgregarLineaGuiaForm guiaRemisionId={guia.guia_remision_id} lineasOc={ordenCompra.detalle} />}
      </div>
    </div>
  );
}
