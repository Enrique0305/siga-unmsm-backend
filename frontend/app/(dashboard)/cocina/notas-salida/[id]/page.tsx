import { notFound } from "next/navigation";

import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { NotaSalidaDetailOut } from "@/lib/api/generated/model/notaSalidaDetailOut";
import type { SolicitudCocinaOut } from "@/lib/api/generated/model/solicitudCocinaOut";

export default async function NotaSalidaDetailPage({
  params,
}: PageProps<"/cocina/notas-salida/[id]">) {
  const { id } = await params;

  let nota: NotaSalidaDetailOut;
  try {
    nota = await serverFetch<NotaSalidaDetailOut>(`/notas-salida/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [almacen, solicitud] = await Promise.all([
    serverFetch<AlmacenOut>(`/almacenes/${nota.almacen_id}`),
    serverFetch<SolicitudCocinaOut>(`/solicitudes-cocina/${nota.solicitud_cocina_id}`),
  ]);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h2 className="text-lg font-semibold text-foreground">{nota.numero_nota}</h2>
        <p className="mt-1 text-sm text-text-secondary">
          Solicitud {solicitud.numero_solicitud} · Almacén {almacen.codigo} — {almacen.nombre}
        </p>
        <p className="mt-1 text-sm text-text-secondary">Fecha de salida: {nota.fecha_salida}</p>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas despachadas</h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Cant. despachada</th>
              <th className="py-2 font-medium">Costo unitario</th>
              <th className="py-2 font-medium">Cant. teórica (BOM)</th>
              <th className="py-2 font-medium">Variación %</th>
            </tr>
          </thead>
          <tbody>
            {nota.detalle.map((linea) => (
              <tr key={linea.nota_salida_detalle_id} className="border-b border-border/10 last:border-0">
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_despachada}</td>
                <td className="py-2">S/ {linea.costo_unitario.toFixed(2)}</td>
                <td className="py-2 text-text-secondary">{linea.cantidad_teorica_bom ?? "—"}</td>
                <td className="py-2 text-text-secondary">
                  {linea.variacion_pct !== null ? `${linea.variacion_pct}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
