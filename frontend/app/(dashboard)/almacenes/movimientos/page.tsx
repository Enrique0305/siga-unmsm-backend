import { AjusteForm } from "@/components/almacenes/AjusteForm";
import { DevolucionForm } from "@/components/almacenes/DevolucionForm";
import { MermaForm } from "@/components/almacenes/MermaForm";
import { serverFetch } from "@/lib/api/server-fetch";
import { getSession } from "@/lib/auth/session";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

const ROLES_EDICION = ["ADMIN", "ALMACENERO"];

export default async function MovimientosAlmacenPage() {
  const [session, almacenes, productos] = await Promise.all([
    getSession(),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
  ]);

  if (!session || !ROLES_EDICION.includes(session.rol)) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        No tienes permisos para registrar movimientos de almacén.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-text-secondary">
        Estas 3 acciones no tienen historial propio — el resultado se ve en
        Stock y Kardex.
      </p>
      <AjusteForm almacenes={almacenes.items} productos={productos.items} />
      <MermaForm almacenes={almacenes.items} productos={productos.items} />
      <DevolucionForm almacenes={almacenes.items} productos={productos.items} />
    </div>
  );
}
