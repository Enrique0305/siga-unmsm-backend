import { notFound } from "next/navigation";

import { UsuarioForm } from "@/components/administracion/UsuarioForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { PageAlmacenOut } from "@/lib/api/generated/model/pageAlmacenOut";
import type { PageUsuarioOut } from "@/lib/api/generated/model/pageUsuarioOut";
import type { RolOut } from "@/lib/api/generated/model/rolOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";

export default async function EditarUsuarioPage({
  params,
}: PageProps<"/administracion/[id]/editar">) {
  const { id } = await params;

  const usuarios = await serverFetch<PageUsuarioOut>("/usuarios?page_size=100");
  const usuario = usuarios.items.find((item) => item.usuario_id === Number(id));
  if (!usuario) {
    notFound();
  }

  const [roles, sedes, almacenes] = await Promise.all([
    serverFetch<RolOut[]>("/catalogos/roles"),
    serverFetch<SedeOut[]>("/catalogos/sedes"),
    serverFetch<PageAlmacenOut>("/almacenes?page_size=100"),
  ]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">
        Editar usuario — {usuario.nombres} {usuario.apellidos}
      </h2>
      <UsuarioForm
        mode="edit"
        usuario={usuario}
        roles={roles}
        sedes={sedes}
        almacenes={almacenes.items}
      />
    </div>
  );
}
