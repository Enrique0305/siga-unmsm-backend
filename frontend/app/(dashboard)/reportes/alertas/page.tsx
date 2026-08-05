import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { AlertasAlmacenOut } from "@/lib/api/generated/model/alertasAlmacenOut";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

export default async function AlertasPage({
  searchParams,
}: PageProps<"/reportes/alertas">) {
  const params = await searchParams;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";
  const diasVencimiento = typeof params.dias_vencimiento === "string" ? params.dias_vencimiento : "";
  const productoId = typeof params.producto_id === "string" ? params.producto_id : "";

  const query = new URLSearchParams();
  if (almacenId) query.set("almacen_id", almacenId);
  if (diasVencimiento) query.set("dias_vencimiento", diasVencimiento);
  if (productoId) query.set("producto_id", productoId);

  const [almacenes, productos, alertas] = await Promise.all([
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
    serverFetch<AlertasAlmacenOut>(`/reportes/alertas?${query.toString()}`),
  ]);

  return (
    <div className="space-y-6">
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
          paramName="dias_vencimiento"
          label="Días para vencimiento"
          options={[
            { value: "", label: "Predeterminado del sistema" },
            { value: "7", label: "7 días" },
            { value: "15", label: "15 días" },
            { value: "30", label: "30 días" },
            { value: "60", label: "60 días" },
          ]}
        />
        <SelectFilter
          paramName="producto_id"
          label="Producto"
          options={[
            { value: "", label: "Todos" },
            ...productos.items.map((producto) => ({
              value: String(producto.producto_id),
              label: `${producto.codigo} — ${producto.nombre}`,
            })),
          ]}
        />
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Stock bajo</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="px-4 py-3 font-medium">Almacén</th>
                <th className="px-4 py-3 font-medium">Producto</th>
                <th className="px-4 py-3 font-medium">Stock físico</th>
                <th className="px-4 py-3 font-medium">Stock mínimo</th>
              </tr>
            </thead>
            <tbody>
              {alertas.stock_bajo.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-center text-text-secondary">
                    Sin alertas de stock bajo.
                  </td>
                </tr>
              )}
              {alertas.stock_bajo.map((fila, index) => (
                <tr key={index} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-3 text-text-secondary">#{fila.almacen_id}</td>
                  <td className="px-4 py-3">
                    {fila.producto_codigo} — {fila.producto_nombre}
                  </td>
                  <td className="px-4 py-3">{fila.stock_fisico}</td>
                  <td className="px-4 py-3">{fila.stock_minimo_referencial}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Próximos a vencer</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="px-4 py-3 font-medium">Almacén</th>
                <th className="px-4 py-3 font-medium">Producto</th>
                <th className="px-4 py-3 font-medium">Lote</th>
                <th className="px-4 py-3 font-medium">Vencimiento</th>
                <th className="px-4 py-3 font-medium">Cant. ingresada</th>
              </tr>
            </thead>
            <tbody>
              {alertas.proximos_vencer.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-text-secondary">
                    Sin lotes próximos a vencer.
                  </td>
                </tr>
              )}
              {alertas.proximos_vencer.map((fila, index) => (
                <tr key={index} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-3 text-text-secondary">#{fila.almacen_id}</td>
                  <td className="px-4 py-3">
                    {fila.producto_codigo} — {fila.producto_nombre}
                  </td>
                  <td className="px-4 py-3">{fila.lote ?? "—"}</td>
                  <td className="px-4 py-3">{fila.fecha_vencimiento}</td>
                  <td className="px-4 py-3">{fila.cantidad_ingresada}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-foreground">Observaciones sin resolver</h3>
        <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="px-4 py-3 font-medium">Almacén</th>
                <th className="px-4 py-3 font-medium">Guía</th>
                <th className="px-4 py-3 font-medium">Producto</th>
                <th className="px-4 py-3 font-medium">Cant. observada</th>
                <th className="px-4 py-3 font-medium">Estado acta</th>
              </tr>
            </thead>
            <tbody>
              {alertas.observaciones_sin_resolver.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-text-secondary">
                    Sin observaciones pendientes.
                  </td>
                </tr>
              )}
              {alertas.observaciones_sin_resolver.map((fila) => (
                <tr key={fila.guia_remision_id} className="border-b border-border/10 last:border-0">
                  <td className="px-4 py-3 text-text-secondary">#{fila.almacen_id}</td>
                  <td className="px-4 py-3">{fila.numero_guia}</td>
                  <td className="px-4 py-3">
                    {fila.producto_codigo} — {fila.producto_nombre}
                  </td>
                  <td className="px-4 py-3">{fila.cantidad_observada}</td>
                  <td className="px-4 py-3">{fila.acta_estado ?? "Sin acta"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
