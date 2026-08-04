import { notFound } from "next/navigation";

import { AgregarProductoContratadoForm } from "@/components/contratos/AgregarProductoContratadoForm";
import { CambiarEstadoContrato } from "@/components/contratos/CambiarEstadoContrato";
import { Badge } from "@/components/ui/Badge";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { ContratoDetailOut } from "@/lib/api/generated/model/contratoDetailOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];

const ESTADO_VARIANT: Record<string, "success" | "warning" | "neutral"> = {
  VIGENTE: "success",
  SUSPENDIDO: "warning",
  CERRADO: "neutral",
};

export default async function ContratoDetailPage({
  params,
}: PageProps<"/proveedores/contratos/[id]">) {
  const { id } = await params;

  let contrato: ContratoDetailOut;
  try {
    contrato = await serverFetch<ContratoDetailOut>(`/contratos/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [session, productos] = await Promise.all([
    getSession(),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border/20 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-foreground">
              {contrato.numero_contrato}
            </h2>
            <p className="text-sm text-text-secondary">
              {contrato.proveedor_razon_social} ({contrato.proveedor_ruc})
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              label={contrato.estado}
              variant={ESTADO_VARIANT[contrato.estado] ?? "neutral"}
            />
            {contrato.alerta_vigencia && (
              <Badge label={`Vence en ${contrato.dias_para_vencer} días`} variant="danger" />
            )}
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-1 gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-text-secondary">Vigencia</dt>
            <dd>{contrato.fecha_inicio} — {contrato.fecha_fin}</dd>
          </div>
          <div>
            <dt className="text-text-secondary">Presupuesto total</dt>
            <dd>
              S/{" "}
              {contrato.presupuesto_total.toLocaleString("es-PE", {
                minimumFractionDigits: 2,
              })}
            </dd>
          </div>
          <div>
            <dt className="text-text-secondary">Requerimiento anual</dt>
            <dd>#{contrato.requerimiento_anual_id}</dd>
          </div>
        </dl>

        {contrato.condiciones && (
          <p className="mt-4 text-sm text-text-secondary">{contrato.condiciones}</p>
        )}

        {puedeEditar && (
          <div className="mt-4">
            <CambiarEstadoContrato contratoId={contrato.contrato_id} estadoActual={contrato.estado} />
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Cronograma de entrega</h3>
        {contrato.cronograma.length === 0 ? (
          <p className="text-sm text-text-secondary">Sin filas de cronograma.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border/20 text-text-secondary">
              <tr>
                <th className="py-2 font-medium">Periodo</th>
                <th className="py-2 font-medium">Fecha programada</th>
              </tr>
            </thead>
            <tbody>
              {contrato.cronograma.map((fila) => (
                <tr key={fila.cronograma_id} className="border-b border-border/10 last:border-0">
                  <td className="py-2">{fila.periodo}</td>
                  <td className="py-2">{fila.fecha_programada}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="rounded-lg border border-border/20 bg-white p-6">
        <h3 className="mb-3 text-sm font-semibold text-foreground">Productos contratados</h3>
        {contrato.productos_contratados.length === 0 ? (
          <p className="mb-4 text-sm text-text-secondary">Sin productos contratados.</p>
        ) : (
          <div className="mb-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border/20 text-text-secondary">
                <tr>
                  <th className="py-2 font-medium">Producto</th>
                  <th className="py-2 font-medium">Precio</th>
                  <th className="py-2 font-medium">Cantidad</th>
                  <th className="py-2 font-medium">Tope monetario</th>
                  <th className="py-2 font-medium">Saldo físico</th>
                  <th className="py-2 font-medium">Saldo monetario</th>
                  <th className="py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {contrato.productos_contratados.map((producto) => (
                  <tr
                    key={producto.producto_contratado_id}
                    className="border-b border-border/10 last:border-0"
                  >
                    <td className="py-2">
                      {producto.producto_codigo} — {producto.producto_nombre}
                    </td>
                    <td className="py-2">S/ {producto.precio_unitario.toFixed(2)}</td>
                    <td className="py-2">{producto.cantidad_contratada}</td>
                    <td className="py-2">S/ {producto.tope_monetario.toFixed(2)}</td>
                    <td className="py-2">
                      {producto.saldo_fisico} ({producto.porcentaje_saldo_fisico}%)
                    </td>
                    <td className="py-2">
                      S/ {producto.saldo_monetario.toFixed(2)} (
                      {producto.porcentaje_saldo_monetario}%)
                    </td>
                    <td className="py-2">
                      {producto.alerta_saldo && (
                        <Badge label="Saldo bajo" variant="danger" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {puedeEditar && (
          <AgregarProductoContratadoForm
            contratoId={contrato.contrato_id}
            productos={productos.items}
          />
        )}
      </div>
    </div>
  );
}
