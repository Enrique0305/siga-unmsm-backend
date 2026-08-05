import { MarcarLeidaButton } from "@/components/reportes/MarcarLeidaButton";
import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageNotificacionOut } from "@/lib/api/generated/model/pageNotificacionOut";

const PAGE_SIZE = 20;

export default async function NotificacionesPage({
  searchParams,
}: PageProps<"/reportes/notificaciones">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const leida = typeof params.leida === "string" ? params.leida : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (leida) query.set("leida", leida);

  const data = await serverFetch<PageNotificacionOut>(`/notificaciones?${query.toString()}`);

  return (
    <div className="space-y-4">
      <SelectFilter
        paramName="leida"
        label="Estado"
        options={[
          { value: "", label: "Todas" },
          { value: "false", label: "No leídas" },
          { value: "true", label: "Leídas" },
        ]}
      />

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Tipo</th>
              <th className="px-4 py-3 font-medium">Mensaje</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
              <th className="px-4 py-3 font-medium">Estado</th>
              <th className="px-4 py-3 font-medium">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                  Sin notificaciones para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((n) => (
              <tr key={n.notificacion_id} className="border-b border-border/10 last:border-0 align-top">
                <td className="px-4 py-3">
                  <Badge
                    label={n.tipo}
                    variant={n.tipo === "CONTRATO_SALDO" ? "danger" : "warning"}
                  />
                </td>
                <td className="px-4 py-3">{n.mensaje}</td>
                <td className="px-4 py-3 text-text-secondary">{n.creado_en}</td>
                <td className="px-4 py-3">
                  <Badge
                    label={n.leida ? "Leída" : "Nueva"}
                    variant={n.leida ? "neutral" : "primary"}
                  />
                </td>
                <td className="px-4 py-3">
                  {!n.leida && <MarcarLeidaButton notificacionId={n.notificacion_id} />}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-4">
          <Pagination page={data.page} pageSize={data.page_size} total={data.total} />
        </div>
      </div>
    </div>
  );
}
