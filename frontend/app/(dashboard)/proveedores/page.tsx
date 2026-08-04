import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Pagination } from "@/components/ui/Pagination";
import { SearchBar } from "@/components/ui/SearchBar";
import { SelectFilter } from "@/components/ui/SelectFilter";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageProveedorOut } from "@/lib/api/generated/model/pageProveedorOut";

const ROLES_EDICION = ["ADMIN", "LOGISTICA_CENTRAL"];
const PAGE_SIZE = 20;

export default async function ProveedoresPage({
  searchParams,
}: PageProps<"/proveedores">) {
  const params = await searchParams;
  const page = Number(params.page ?? "1") || 1;
  const estado = typeof params.estado === "string" ? params.estado : "ACTIVO";
  const buscar = typeof params.buscar === "string" ? params.buscar : "";

  const [session, data] = await Promise.all([
    getSession(),
    serverFetch<PageProveedorOut>(
      `/proveedores?page=${page}&page_size=${PAGE_SIZE}&estado=${encodeURIComponent(estado)}${
        buscar ? `&buscar=${encodeURIComponent(buscar)}` : ""
      }`,
    ),
  ]);

  const puedeEditar = session ? ROLES_EDICION.includes(session.rol) : false;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar placeholder="Buscar por razón social o RUC..." />
          <SelectFilter
            paramName="estado"
            label="Estado"
            options={[
              { value: "ACTIVO", label: "Activos" },
              { value: "INACTIVO", label: "Inactivos" },
            ]}
          />
        </div>
        {puedeEditar && (
          <Link
            href="/proveedores/nuevo"
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Nuevo proveedor
          </Link>
        )}
      </div>

      <div className="overflow-x-auto rounded-lg border border-border/20 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border/20 text-text-secondary">
            <tr>
              <th className="px-4 py-3 font-medium">RUC</th>
              <th className="px-4 py-3 font-medium">Razón social</th>
              <th className="px-4 py-3 font-medium">Contacto</th>
              <th className="px-4 py-3 font-medium">Estado</th>
              {puedeEditar && <th className="px-4 py-3 font-medium" />}
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 && (
              <tr>
                <td
                  colSpan={puedeEditar ? 5 : 4}
                  className="px-4 py-8 text-center text-text-secondary"
                >
                  No hay proveedores para mostrar.
                </td>
              </tr>
            )}
            {data.items.map((proveedor) => (
              <tr key={proveedor.proveedor_id} className="border-b border-border/10 last:border-0">
                <td className="px-4 py-3 font-mono text-xs">{proveedor.ruc}</td>
                <td className="px-4 py-3">{proveedor.razon_social}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {proveedor.contacto_nombre ?? "—"}
                  {proveedor.contacto_correo && (
                    <span className="block text-xs">{proveedor.contacto_correo}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <Badge
                    label={proveedor.estado}
                    variant={proveedor.estado === "ACTIVO" ? "success" : "neutral"}
                  />
                </td>
                {puedeEditar && (
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/proveedores/${proveedor.proveedor_id}/editar`}
                      className="text-primary hover:underline"
                    >
                      Editar
                    </Link>
                  </td>
                )}
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
