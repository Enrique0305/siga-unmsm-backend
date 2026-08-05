import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAuditoriaLogOut } from "@/lib/api/generated/model/pageAuditoriaLogOut";

const PAGE_SIZE = 20;

export default async function AuditoriaPage({
  searchParams,
}: PageProps<"/reportes/auditoria">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const entidad = typeof params.entidad === "string" ? params.entidad : "";
  const entidadId = typeof params.entidad_id === "string" ? params.entidad_id : "";
  const usuarioId = typeof params.usuario_id === "string" ? params.usuario_id : "";

  const query = new URLSearchParams();
  query.set("page", String(page));
  query.set("page_size", String(PAGE_SIZE));
  if (entidad) query.set("entidad", entidad);
  if (entidadId) query.set("entidad_id", entidadId);
  if (usuarioId) query.set("usuario_id", usuarioId);

  const data = await serverFetch<PageAuditoriaLogOut>(`/auditoria?${query.toString()}`);

  return (
    <div className="space-y-4">
      <form className="flex flex-wrap items-end gap-3 rounded-lg border border-border/20 bg-white p-4">
        <div className="space-y-1">
          <label htmlFor="entidad" className="text-sm font-medium">
            Entidad
          </label>
          <input
            id="entidad"
            name="entidad"
            defaultValue={entidad}
            placeholder="contrato, orden_compra..."
            className="w-48 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="entidad_id" className="text-sm font-medium">
            ID de entidad
          </label>
          <input
            id="entidad_id"
            name="entidad_id"
            type="number"
            defaultValue={entidadId}
            className="w-32 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="usuario_id" className="text-sm font-medium">
            Usuario
          </label>
          <input
            id="usuario_id"
            name="usuario_id"
            type="number"
            defaultValue={usuarioId}
            className="w-32 rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <button
          type="submit"
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
        >
          Filtrar
        </button>
      </form>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Entidad</th>
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Acción</th>
              <th className="px-4 py-3 font-medium">Usuario</th>
              <th className="px-4 py-3 font-medium">Detalle</th>
              <th className="px-4 py-3 font-medium">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                  Sin registros de auditoría para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((log) => (
              <tr key={log.auditoria_id} className="border-b border-border/10 last:border-0 align-top">
                <td className="px-4 py-3">{log.entidad}</td>
                <td className="px-4 py-3">{log.entidad_id}</td>
                <td className="px-4 py-3">{log.accion}</td>
                <td className="px-4 py-3 text-text-secondary">{log.usuario_nombre}</td>
                <td className="px-4 py-3">
                  {log.detalle_json ? (
                    <pre className="max-w-xs overflow-x-auto whitespace-pre-wrap text-xs text-text-secondary">
                      {JSON.stringify(log.detalle_json, null, 2)}
                    </pre>
                  ) : (
                    <span className="text-text-secondary">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-text-secondary">{log.creado_en}</td>
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
