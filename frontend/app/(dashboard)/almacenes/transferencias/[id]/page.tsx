import { notFound } from "next/navigation";

import { TransferenciaRecepcionForm } from "@/components/almacenes/TransferenciaRecepcionForm";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { TransferenciaAlmacenDetailOut } from "@/lib/api/generated/model/transferenciaAlmacenDetailOut";

const ROLES_EDICION = ["ADMIN", "ALMACENERO"];

const ESTADO_VARIANT: Record<string, "warning" | "success" | "danger" | "neutral"> = {
  EN_TRANSITO: "warning",
  RECIBIDA_CONFORME: "success",
  RECIBIDA_CON_DIFERENCIA: "danger",
  ANULADA: "neutral",
};

export default async function TransferenciaDetailPage({
  params,
}: PageProps<"/almacenes/transferencias/[id]">) {
  const { id } = await params;

  let transferencia: TransferenciaAlmacenDetailOut;
  try {
    transferencia = await serverFetch<TransferenciaAlmacenDetailOut>(`/transferencias/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, almacenOrigen, almacenDestino] = await Promise.all([
    getSession(),
    serverFetch<AlmacenOut>(`/almacenes/${transferencia.almacen_origen_id}`),
    serverFetch<AlmacenOut>(`/almacenes/${transferencia.almacen_destino_id}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {transferencia.numero_transferencia}
            </h2>
            <p className="mt-1 text-sm text-text-secondary">
              {almacenOrigen.codigo} — {almacenOrigen.nombre} → {almacenDestino.codigo} —{" "}
              {almacenDestino.nombre}
            </p>
          </div>
          <Badge
            label={transferencia.estado}
            variant={ESTADO_VARIANT[transferencia.estado] ?? "neutral"}
          />
        </div>
        <p className="mt-2 text-sm text-text-secondary">
          Fecha de salida: {transferencia.fecha_salida}
          {transferencia.fecha_recepcion && ` · Fecha de recepción: ${transferencia.fecha_recepcion}`}
        </p>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas</h3>
        <table className="mb-4 w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Enviada</th>
              <th className="py-2 font-medium">Recibida</th>
              <th className="py-2 font-medium">Diferencia</th>
              <th className="py-2 font-medium">Observación</th>
            </tr>
          </thead>
          <tbody>
            {transferencia.detalle.map((linea) => (
              <tr key={linea.transferencia_detalle_id} className="border-b border-border/10 last:border-0">
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_enviada}</td>
                <td className="py-2">{linea.cantidad_recibida ?? "—"}</td>
                <td className="py-2">{linea.diferencia}</td>
                <td className="py-2 text-text-secondary">
                  {linea.observacion_diferencia ?? "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {puedeEditar && transferencia.estado === "EN_TRANSITO" && (
          <TransferenciaRecepcionForm
            transferenciaId={transferencia.transferencia_id}
            lineas={transferencia.detalle}
          />
        )}
      </div>
    </div>
  );
}
