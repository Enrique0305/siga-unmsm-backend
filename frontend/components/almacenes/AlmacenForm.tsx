"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import {
  useActualizarAlmacenApiV1AlmacenesAlmacenIdPatch,
  useCrearAlmacenApiV1AlmacenesPost,
} from "@/lib/api/generated/endpoints/almacenes/almacenes";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";
import type { UsuarioOut } from "@/lib/api/generated/model/usuarioOut";

export function AlmacenForm({
  mode,
  almacen,
  sedes,
  usuarios,
}: {
  mode: "create" | "edit";
  almacen?: AlmacenOut;
  sedes: SedeOut[];
  usuarios: UsuarioOut[];
}) {
  const router = useRouter();
  const crear = useCrearAlmacenApiV1AlmacenesPost();
  const actualizar = useActualizarAlmacenApiV1AlmacenesAlmacenIdPatch();

  const [codigo, setCodigo] = useState(almacen?.codigo ?? "");
  const [nombre, setNombre] = useState(almacen?.nombre ?? "");
  const [sedeId, setSedeId] = useState<number | string>(
    almacen?.sede_id ?? sedes[0]?.sede_id ?? "",
  );
  const [direccion, setDireccion] = useState(almacen?.direccion ?? "");
  const [tipoComedor, setTipoComedor] = useState(almacen?.tipo_comedor ?? "");
  const [responsableId, setResponsableId] = useState<number | string>(
    almacen?.responsable_id ?? usuarios[0]?.usuario_id ?? "",
  );
  const [estado, setEstado] = useState(almacen?.estado ?? "ACTIVO");
  const [error, setError] = useState<string | null>(null);

  const isPending = crear.isPending || actualizar.isPending;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (mode === "create") {
      const response = await crear.mutateAsync({
        data: {
          codigo,
          nombre,
          sede_id: Number(sedeId),
          direccion: direccion || null,
          tipo_comedor: tipoComedor,
          responsable_id: Number(responsableId),
        },
      });
      if (response.status !== 201) {
        setError(extractErrorMessage(response.data));
        return;
      }
    } else if (almacen) {
      const response = await actualizar.mutateAsync({
        almacenId: almacen.almacen_id,
        data: {
          nombre,
          direccion: direccion || null,
          tipo_comedor: tipoComedor,
          responsable_id: Number(responsableId),
          estado,
        },
      });
      if (response.status !== 200) {
        setError(extractErrorMessage(response.data));
        return;
      }
    }

    router.push("/almacenes");
    router.refresh();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="space-y-1">
        <label htmlFor="codigo" className="text-sm font-medium">
          Código
        </label>
        <input
          id="codigo"
          value={codigo}
          onChange={(event) => setCodigo(event.target.value)}
          required
          maxLength={20}
          disabled={mode === "edit"}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:bg-surface disabled:text-text-secondary"
        />
        {mode === "edit" && (
          <p className="text-xs text-text-secondary">El código no se puede modificar.</p>
        )}
      </div>

      <div className="space-y-1">
        <label htmlFor="nombre" className="text-sm font-medium">
          Nombre
        </label>
        <input
          id="nombre"
          value={nombre}
          onChange={(event) => setNombre(event.target.value)}
          required
          maxLength={200}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="sede_id" className="text-sm font-medium">
            Sede
          </label>
          <select
            id="sede_id"
            value={sedeId}
            onChange={(event) => setSedeId(event.target.value)}
            required
            disabled={mode === "edit"}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:bg-surface disabled:text-text-secondary"
          >
            {sedes.map((sede) => (
              <option key={sede.sede_id} value={sede.sede_id}>
                {sede.nombre}
              </option>
            ))}
          </select>
          {mode === "edit" && (
            <p className="text-xs text-text-secondary">La sede no se puede modificar.</p>
          )}
        </div>
        <div className="space-y-1">
          <label htmlFor="tipo_comedor" className="text-sm font-medium">
            Tipo de comedor
          </label>
          <input
            id="tipo_comedor"
            value={tipoComedor}
            onChange={(event) => setTipoComedor(event.target.value)}
            required
            maxLength={60}
            placeholder="ESTUDIANTES, ADMINISTRATIVOS_DOCENTES..."
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="direccion" className="text-sm font-medium">
          Dirección (opcional)
        </label>
        <input
          id="direccion"
          value={direccion}
          onChange={(event) => setDireccion(event.target.value)}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="responsable_id" className="text-sm font-medium">
          Responsable
        </label>
        <select
          id="responsable_id"
          value={responsableId}
          onChange={(event) => setResponsableId(event.target.value)}
          required
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {usuarios.map((usuario) => (
            <option key={usuario.usuario_id} value={usuario.usuario_id}>
              {usuario.nombres} {usuario.apellidos}
            </option>
          ))}
        </select>
      </div>

      {mode === "edit" && (
        <div className="space-y-1">
          <label htmlFor="estado" className="text-sm font-medium">
            Estado
          </label>
          <select
            id="estado"
            value={estado}
            onChange={(event) => setEstado(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            <option value="ACTIVO">ACTIVO</option>
            <option value="INACTIVO">INACTIVO</option>
          </select>
        </div>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {isPending ? "Guardando..." : "Guardar"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/almacenes")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
