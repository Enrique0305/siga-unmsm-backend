import { notFound } from "next/navigation";

import { AlmacenForm } from "@/components/almacenes/AlmacenForm";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { PageUsuarioOut } from "@/lib/api/generated/model/pageUsuarioOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

export default async function EditarAlmacenPage({
  params,
}: PageProps<"/almacenes/[id]/editar">) {
  const { id } = await params;

  let almacen: AlmacenOut;
  try {
    almacen = await serverFetch<AlmacenOut>(`/almacenes/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  const [sedes, usuarios] = await Promise.all([
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<PageUsuarioOut>("/usuarios?page_size=100"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">
        Editar almacén — {almacen.nombre}
      </h2>
      <AlmacenForm mode="edit" almacen={almacen} sedes={sedes} usuarios={usuarios.items} />
    </div>
  );
}
