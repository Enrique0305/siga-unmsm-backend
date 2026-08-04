import { notFound } from "next/navigation";

import { CerrarInventarioButton } from "@/components/almacenes/CerrarInventarioButton";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { InventarioFisicoDetailOut } from "@/lib/api/generated/model/inventarioFisicoDetailOut";

const ROLES_EDICION = ["ADMIN", "ALMACENERO"];

const ESTADO_VARIANT: Record<string, "warning" | "success"> = {
  EN_PROCESO: "warning",
  CERRADO: "success",
};

export default async function InventarioFisicoDetailPage({
  params,
}: PageProps<"/almacenes/inventarios/[id]">) {
  const { id } = await params;

  let inventario: InventarioFisicoDetailOut;
  try {
    inventario = await serverFetch<InventarioFisicoDetailOut>(`/inventarios-fisicos/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, almacen] = await Promise.all([
    getSession(),
    serverFetch<AlmacenOut>(`/almacenes/${inventario.almacen_id}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {almacen.codigo} — {almacen.nombre}
            </h2>
            <p className="mt-1 text-sm text-text-secondary">
              Fecha de conteo: {inventario.fecha_conteo}
            </p>
          </div>
          <Badge
            label={inventario.estado}
            variant={ESTADO_VARIANT[inventario.estado] ?? "warning"}
          />
        </div>
        {puedeEditar && inventario.estado === "EN_PROCESO" && (
          <div className="mt-4">
            <CerrarInventarioButton inventarioFisicoId={inventario.inventario_fisico_id} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Líneas de conteo</h3>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="py-2 font-medium">Producto</th>
              <th className="py-2 font-medium">Stock sistema</th>
              <th className="py-2 font-medium">Stock contado</th>
              <th className="py-2 font-medium">Diferencia</th>
              <th className="py-2 font-medium">Ajuste generado</th>
            </tr>
          </thead>
          <tbody>
            {inventario.detalle.map((linea) => (
              <tr
                key={linea.inventario_fisico_detalle_id}
                className="border-b border-border/10 last:border-0"
              >
                <td className="py-2">
                  {linea.producto_codigo} — {linea.producto_nombre}
                </td>
                <td className="py-2">{linea.stock_sistema}</td>
                <td className="py-2">{linea.stock_contado}</td>
                <td className="py-2">{linea.diferencia}</td>
                <td className="py-2 text-text-secondary">
                  {linea.ajuste_generado_id ? `#${linea.ajuste_generado_id}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
