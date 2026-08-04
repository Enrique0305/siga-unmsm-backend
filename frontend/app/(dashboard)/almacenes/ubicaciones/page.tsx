import { UbicacionForm } from "@/components/almacenes/UbicacionForm";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { Pagination } from "@/components/ui/Pagination";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageUbicacionInternaOut } from "@/lib/api/generated/model/pageUbicacionInternaOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL", "ALMACENERO"];
const PAGE_SIZE = 20;

export default async function UbicacionesPage({
  searchParams,
}: PageProps<"/almacenes/ubicaciones">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const almacenId = typeof params.almacen_id === "string" ? params.almacen_id : "";

  const query = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (almacenId) query.set("almacen_id", almacenId);

  const [session, almacenes, data] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageUbicacionInternaOut>(`/ubicaciones?${query.toString()}`),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;
  const nombreAlmacen = new Map(almacenes.items.map((a) => [a.almacen_id, `${a.codigo} — ${a.nombre}`]));

  return (
    <div className="space-y-4">
      {puedeEditar && <UbicacionForm almacenes={almacenes.items} />}

      <SelectFilter
        paramName="almacen_id"
        label="Almacén"
        options={[
          { value: "", label: "Todos" },
          ...almacenes.items.map((a) => ({ value: String(a.almacen_id), label: a.codigo })),
        ]}
      />

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">Almacén</th>
              <th className="px-4 py-3 font-medium">Zona</th>
              <th className="px-4 py-3 font-medium">Estante</th>
              <th className="px-4 py-3 font-medium">Nivel</th>
              <th className="px-4 py-3 font-medium">Contenedor/cámara</th>
              <th className="px-4 py-3 font-medium">Cadena de frío</th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                  No hay ubicaciones para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((ubicacion) => (
              <tr key={ubicacion.ubicacion_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 text-text-secondary">
                  {nombreAlmacen.get(ubicacion.almacen_id) ?? `#${ubicacion.almacen_id}`}
                </td>
                <td className="px-4 py-3">{ubicacion.zona}</td>
                <td className="px-4 py-3 text-text-secondary">{ubicacion.estante ?? "—"}</td>
                <td className="px-4 py-3 text-text-secondary">{ubicacion.nivel ?? "—"}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {ubicacion.contenedor_camara ?? "—"}
                </td>
                <td className="px-4 py-3 text-text-secondary">
                  {ubicacion.es_cadena_frio ? "Sí" : "No"}
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
