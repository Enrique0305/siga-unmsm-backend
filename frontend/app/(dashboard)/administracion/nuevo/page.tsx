import { UsuarioForm } from "@/components/administracion/UsuarioForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageProveedorOut } from "@/lib/api/generated/model/pageProveedorOut";
import type { RolOut } from "@/lib/api/generated/model/rolOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

export default async function NuevoUsuarioPage() {
  const [roles, sedes, almacenes, proveedores] = await Promise.all([
    serverFetch<RolOut[]>("/catalogos/roles"),
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProveedorOut>("/proveedores?page_size=100"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo usuario</h2>
      <UsuarioForm
        mode="create"
        roles={roles}
        sedes={sedes}
        almacenes={almacenes.items}
        proveedores={proveedores.items}
      />
    </div>
  );
}
