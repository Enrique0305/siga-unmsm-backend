"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import {
  useActualizarUsuarioApiV1UsuariosUsuarioIdPatch,
  useCrearUsuarioApiV1UsuariosPost,
} from "@/lib/api/generated/endpoints/usuarios/usuarios";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { ProveedorOut } from "@/lib/api/generated/model/proveedorOut";
import type { RolOut } from "@/lib/api/generated/model/rolOut";
import type { SedeOut } from "@/lib/api/generated/model/sedeOut";
import type { UsuarioOut } from "@/lib/api/generated/model/usuarioOut";

export function UsuarioForm({
  mode,
  usuario,
  roles,
  sedes,
  almacenes,
  proveedores,
}: {
  mode: "create" | "edit";
  usuario?: UsuarioOut;
  roles: RolOut[];
  sedes: SedeOut[];
  almacenes: AlmacenOut[];
  proveedores: ProveedorOut[];
}) {
  const router = useRouter();
  const crear = useCrearUsuarioApiV1UsuariosPost();
  const actualizar = useActualizarUsuarioApiV1UsuariosUsuarioIdPatch();

  const [nombres, setNombres] = useState(usuario?.nombres ?? "");
  const [apellidos, setApellidos] = useState(usuario?.apellidos ?? "");
  const [correo, setCorreo] = useState(usuario?.correo ?? "");
  const [password, setPassword] = useState("");
  const [rolId, setRolId] = useState<number | string>(
    usuario?.rol.rol_id ?? roles[0]?.rol_id ?? "",
  );
  const [sedeId, setSedeId] = useState<number | string>("");
  const [proveedorId, setProveedorId] = useState<number | string>(usuario?.proveedor_id ?? "");
  const [almacenIds, setAlmacenIds] = useState<number[]>(usuario?.almacen_ids ?? []);
  const [estado, setEstado] = useState(usuario?.estado ?? "ACTIVO");
  const [error, setError] = useState<string | null>(null);

  const rolSeleccionado = useMemo(
    () => roles.find((rol) => rol.rol_id === Number(rolId)),
    [roles, rolId],
  );
  const isPending = crear.isPending || actualizar.isPending;

  function toggleAlmacen(almacenId: number) {
    setAlmacenIds((current) =>
      current.includes(almacenId)
        ? current.filter((id) => id !== almacenId)
        : [...current, almacenId],
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (mode === "create") {
      const response = await crear.mutateAsync({
        data: {
          nombres,
          apellidos,
          correo,
          password,
          rol_id: Number(rolId),
          sede_id: sedeId ? Number(sedeId) : null,
          proveedor_id: proveedorId ? Number(proveedorId) : null,
          almacen_ids: almacenIds,
        },
      });
      if (response.status !== 201) {
        setError(extractErrorMessage(response.data));
        return;
      }
    } else if (usuario) {
      const response = await actualizar.mutateAsync({
        usuarioId: usuario.usuario_id,
        data: {
          nombres,
          apellidos,
          rol_id: Number(rolId),
          proveedor_id: proveedorId ? Number(proveedorId) : null,
          almacen_ids: almacenIds,
          estado,
        },
      });
      if (response.status !== 200) {
        setError(extractErrorMessage(response.data));
        return;
      }
    }

    router.push("/administracion");
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="nombres" className="text-sm font-medium">
            Nombres
          </label>
          <input
            id="nombres"
            value={nombres}
            onChange={(event) => setNombres(event.target.value)}
            required
            maxLength={150}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="apellidos" className="text-sm font-medium">
            Apellidos
          </label>
          <input
            id="apellidos"
            value={apellidos}
            onChange={(event) => setApellidos(event.target.value)}
            required
            maxLength={150}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="correo" className="text-sm font-medium">
          Correo
        </label>
        <input
          id="correo"
          type="email"
          value={correo}
          onChange={(event) => setCorreo(event.target.value)}
          required
          disabled={mode === "edit"}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:bg-surface disabled:text-text-secondary"
        />
        {mode === "edit" && (
          <p className="text-xs text-text-secondary">El correo no se puede modificar.</p>
        )}
      </div>

      {mode === "create" && (
        <div className="space-y-1">
          <label htmlFor="password" className="text-sm font-medium">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={8}
            maxLength={128}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="rol_id" className="text-sm font-medium">
            Rol
          </label>
          <select
            id="rol_id"
            value={rolId}
            onChange={(event) => setRolId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {roles.map((rol) => (
              <option key={rol.rol_id} value={rol.rol_id}>
                {rol.nombre}
              </option>
            ))}
          </select>
        </div>
        {mode === "create" && (
          <div className="space-y-1">
            <label htmlFor="sede_id" className="text-sm font-medium">
              Sede (opcional)
            </label>
            <select
              id="sede_id"
              value={sedeId}
              onChange={(event) => setSedeId(event.target.value)}
              className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
            >
              <option value="">Sin sede</option>
              {sedes.map((sede) => (
                <option key={sede.sede_id} value={sede.sede_id}>
                  {sede.nombre}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
      {mode === "edit" && (
        <p className="text-xs text-text-secondary">
          La sede asignada solo se define al crear el usuario.
        </p>
      )}

      {rolSeleccionado?.nombre === "PROVEEDOR" && (
        <div className="space-y-1">
          <label htmlFor="proveedor_id" className="text-sm font-medium">
            Proveedor
          </label>
          <select
            id="proveedor_id"
            value={proveedorId}
            onChange={(event) => setProveedorId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            <option value="">Selecciona un proveedor</option>
            {proveedores.map((proveedor) => (
              <option key={proveedor.proveedor_id} value={proveedor.proveedor_id}>
                {proveedor.razon_social}
              </option>
            ))}
          </select>
          <p className="text-xs text-text-secondary">
            Acota qué contratos, órdenes de compra y guías puede ver este usuario.
          </p>
        </div>
      )}

      {rolSeleccionado?.acceso_todos_almacenes ? (
        <p className="rounded-md bg-primary/10 px-3 py-2 text-xs text-primary">
          Este rol ya tiene acceso a todos los almacenes (RN-20) — no hace falta asignarlos.
        </p>
      ) : (
        <div className="space-y-1">
          <span className="text-sm font-medium">Almacenes autorizados (RN-20)</span>
          <div className="flex flex-wrap gap-3 rounded-md border border-border/30 p-3">
            {almacenes.map((almacen) => (
              <label key={almacen.almacen_id} className="flex items-center gap-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={almacenIds.includes(almacen.almacen_id)}
                  onChange={() => toggleAlmacen(almacen.almacen_id)}
                />
                {almacen.codigo}
              </label>
            ))}
          </div>
        </div>
      )}

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
          onClick={() => router.push("/administracion")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
