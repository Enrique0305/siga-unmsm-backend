import { notFound } from "next/navigation";

import { ProveedorForm } from "@/components/proveedores/ProveedorForm";
import { ServerFetchError, serverFetch } from "@/lib/api/server-fetch";
import type { ProveedorOut } from "@/lib/api/generated/model/proveedorOut";

export default async function EditarProveedorPage({
  params,
}: PageProps<"/proveedores/[id]/editar">) {
  const { id } = await params;

  let proveedor: ProveedorOut;
  try {
    proveedor = await serverFetch<ProveedorOut>(`/proveedores/${id}`);
  } catch (error) {
    if (error instanceof ServerFetchError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">
        Editar proveedor — {proveedor.razon_social}
      </h2>
      <ProveedorForm mode="edit" proveedor={proveedor} />
    </div>
  );
}
