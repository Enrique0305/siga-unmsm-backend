import { notFound } from "next/navigation";

import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import type { GuiaRemisionListOut } from "@/lib/api/generated/model/guiaRemisionListOut";
import type { IngresoAlmacenDetailOut } from "@/lib/api/generated/model/ingresoAlmacenDetailOut";

export default async function IngresoAlmacenDetailPage({
  params,
}: PageProps<"/almacenes/ingresos/[id]">) {
  const { id } = await params;

  let ingreso: IngresoAlmacenDetailOut;
  try {
    ingreso = await serverFetch<IngresoAlmacenDetailOut>(`/ingresos-almacen/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const guia = await serverFetch<GuiaRemisionListOut>(`/guias-remision/${ingreso.guia_remision_id}`);

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h2 className="text-lg font-semibold text-foreground">{ingreso.numero_ingreso}</h2>
        <p className="mt-1 text-sm text-text-secondary">
          Guía {guia.numero_guia} · Destino {guia.almacen_destino_codigo} —{" "}
          {guia.almacen_destino_nombre}
        </p>
        <p className="mt-1 text-sm text-text-secondary">
          Fecha de ingreso: {ingreso.fecha_ingreso}
        </p>
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas ingresadas</h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Cantidad ingresada</th>
              <th className="py-2 font-medium">Costo unitario</th>
            </tr>
          </thead>
          <tbody>
            {ingreso.detalle.map((linea) => (
              <tr key={linea.ingreso_almacen_detalle_id} className="border-b border-border/10 last:border-0">
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.cantidad_ingresada}</td>
                <td className="py-2">S/ {linea.costo_unitario.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
