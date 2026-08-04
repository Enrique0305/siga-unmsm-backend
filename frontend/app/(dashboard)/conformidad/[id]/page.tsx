import { notFound } from "next/navigation";
import Link from "next/link";

import { CambiarEstadoInformeForm } from "@/components/conformidad/CambiarEstadoInformeForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { InformeConformidadPagoDetailOut } from "@/lib/api/generated/model/informeConformidadPagoDetailOut";
import type { OrdenCompraOut } from "@/lib/api/generated/model/ordenCompraOut";

const ROLES_ESTADO = ["ADMIN", "PAGOS"];

const ESTADO_VARIANT: Record<string, "neutral" | "warning" | "success" | "danger"> = {
  ENVIADO: "neutral",
  RECIBIDO: "warning",
  EN_PROCESO_DE_PAGO: "warning",
  PAGADO: "success",
  DEVUELTO: "danger",
};

export default async function InformeConformidadDetailPage({
  params,
}: PageProps<"/conformidad/[id]">) {
  const { id } = await params;

  let informe: InformeConformidadPagoDetailOut;
  try {
    informe = await serverFetch<InformeConformidadPagoDetailOut>(
      `/informes-conformidad-pago/${id}`,
    );
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, ordenCompra] = await Promise.all([
    getSession(),
    serverFetch<OrdenCompraOut>(`/ordenes-compra/${informe.orden_compra_id}`),
  ]);

  const puedeCambiarEstado = session ? ROLES_ESTADO.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{informe.numero_informe}</h2>
            <p className="mt-1 text-sm text-text-secondary">
              Orden de compra{" "}
              <Link href={`/compras/${ordenCompra.orden_compra_id}`} className="text-primary hover:underline">
                {ordenCompra.numero_oc}
              </Link>
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              Enviado: {informe.fecha_envio}
              {informe.fecha_pago && ` · Pagado: ${informe.fecha_pago}`}
            </p>
          </div>
          <Badge label={informe.estado} variant={ESTADO_VARIANT[informe.estado] ?? "neutral"} />
        </div>

        <dl className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-text-secondary">Monto conforme</dt>
            <dd className="text-sm font-medium">S/ {informe.monto_conforme_total.toFixed(2)}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Monto retenido</dt>
            <dd className="text-sm font-medium">S/ {informe.monto_retenido_total.toFixed(2)}</dd>
          </div>
          <div>
            <dt className="text-xs text-text-secondary">Monto penalidad</dt>
            <dd className="text-sm font-medium">S/ {informe.monto_penalidad_total.toFixed(2)}</dd>
          </div>
        </dl>

        {puedeCambiarEstado && (
          <div className="mt-4">
            <CambiarEstadoInformeForm informeId={informe.informe_id} estadoActual={informe.estado} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas</h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Cant. conforme</th>
              <th className="py-2 font-medium">Monto conforme</th>
              <th className="py-2 font-medium">Cant. retenida</th>
              <th className="py-2 font-medium">Monto retenido</th>
            </tr>
          </thead>
          <tbody>
            {informe.detalle.map((linea) => (
              <tr key={linea.informe_detalle_id} className="border-b border-border/10 last:border-0">
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_conforme}</td>
                <td className="py-2">S/ {linea.monto_conforme.toFixed(2)}</td>
                <td className="py-2 text-text-secondary">{linea.cantidad_retenida}</td>
                <td className="py-2 text-text-secondary">S/ {linea.monto_retenido.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
