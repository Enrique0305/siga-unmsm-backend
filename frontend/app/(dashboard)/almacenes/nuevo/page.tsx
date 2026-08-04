import { AlmacenForm } from "@/components/almacenes/AlmacenForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageUsuarioOut } from "@/lib/api/generated/model/pageUsuarioOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

export default async function NuevoAlmacenPage() {
  const [sedes, usuarios] = await Promise.all([
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<PageUsuarioOut>("/usuarios?page_size=100"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nuevo almacén</h2>
      <AlmacenForm mode="create" sedes={sedes} usuarios={usuarios.items} />
    </div>
  );
}
