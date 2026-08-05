import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";
import type { ValorizacionAlmacenOut } from "@/lib/api/generated/model/valorizacionAlmacenOut";

export default async function ReportesPage({
  searchParams,
}: PageProps<"/reportes">) {
  const params = await searchParams;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";
  const sedeId = typeof params.sede_id === "string" ? params.sede_id : "";

  const query = new URLSearchParams();
  if (almacenId) query.set("almacen_id", almacenId);
  if (sedeId) query.set("sede_id", sedeId);

  const [almacenes, sedes, valorizacion] = await Promise.all([
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<ValorizacionAlmacenOut[]>(`/reportes/valorizacion-inventario?${query.toString()}`),
  ]);

  const total = valorizacion.reduce((sum, fila) => sum + fila.valor_valorizado_total, 0);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <SelectFilter
          paramName="almacen_id"
          label="Almacén"
          options={[
            { value: "", label: "Todos" },
            ...almacenes.items.map((almacen) => ({
              value: String(almacen.almacen_id),
              label: almacen.codigo,
            })),
          ]}
        />
        <SelectFilter
          paramName="sede_id"
          label="Sede"
          options={[
            { value: "", label: "Todas" },
            ...sedes.map((sede) => ({
              value: String(sede.sede_id),
              label: sede.nombre,
            })),
          ]}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Valor valorizado</th>
            </tr>
          </thead>
          <tbody>
            {valorizacion.length === 0 && (
              <tr>
                <td colSpan={2} className="px-4 py-8 text-center text-text-secondary">
                  Sin datos de valorización.
                </td>
              </tr>
            )}
            {valorizacion.map((fila) => (
              <tr key={fila.almacen_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3">
                  {fila.almacen_codigo} — {fila.almacen_nombre}
                </td>
                <td className="px-4 py-3 font-medium">
                  S/ {fila.valor_valorizado_total.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
          {valorizacion.length > 0 && (
            <tfoot>
              <tr className="border-t border-border/20 font-semibold">
                <td className="px-4 py-3">Total</td>
                <td className="px-4 py-3">S/ {total.toFixed(2)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  );
}
