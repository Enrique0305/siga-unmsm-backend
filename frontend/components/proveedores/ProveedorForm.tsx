"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import {
  useActualizarProveedorApiV1ProveedoresProveedorIdPatch,
  useCrearProveedorApiV1ProveedoresPost,
} from "@/lib/api/generated/endpoints/proveedores/proveedores";
import type { ProveedorOut } from "@/lib/api/generated/model/proveedorOut";

export function ProveedorForm({
  mode,
  proveedor,
}: {
  mode: "create" | "edit";
  proveedor?: ProveedorOut;
}) {
  const router = useRouter();
  const crear = useCrearProveedorApiV1ProveedoresPost();
  const actualizar = useActualizarProveedorApiV1ProveedoresProveedorIdPatch();

  const [ruc, setRuc] = useState(proveedor?.ruc ?? "");
  const [razonSocial, setRazonSocial] = useState(proveedor?.razon_social ?? "");
  const [contactoNombre, setContactoNombre] = useState(proveedor?.contacto_nombre ?? "");
  const [contactoTelefono, setContactoTelefono] = useState(proveedor?.contacto_telefono ?? "");
  const [contactoCorreo, setContactoCorreo] = useState(proveedor?.contacto_correo ?? "");
  const [estado, setEstado] = useState(proveedor?.estado ?? "ACTIVO");
  const [error, setError] = useState<string | null>(null);

  const isPending = crear.isPending || actualizar.isPending;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (mode === "create") {
      const response = await crear.mutateAsync({
        data: {
          ruc,
          razon_social: razonSocial,
          contacto_nombre: contactoNombre || null,
          contacto_telefono: contactoTelefono || null,
          contacto_correo: contactoCorreo || null,
        },
      });
      if (response.status !== 201) {
        setError(extractErrorMessage(response.data));
        return;
      }
    } else if (proveedor) {
      const response = await actualizar.mutateAsync({
        proveedorId: proveedor.proveedor_id,
        data: {
          razon_social: razonSocial,
          contacto_nombre: contactoNombre || null,
          contacto_telefono: contactoTelefono || null,
          contacto_correo: contactoCorreo || null,
          estado,
        },
      });
      if (response.status !== 200) {
        setError(extractErrorMessage(response.data));
        return;
      }
    }

    router.push("/proveedores");
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
        <label htmlFor="ruc" className="text-sm font-medium">
          RUC
        </label>
        <input
          id="ruc"
          value={ruc}
          onChange={(event) => setRuc(event.target.value)}
          required
          minLength={11}
          maxLength={11}
          disabled={mode === "edit"}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none disabled:bg-surface disabled:text-text-secondary"
        />
        {mode === "edit" && (
          <p className="text-xs text-text-secondary">El RUC no se puede modificar.</p>
        )}
      </div>

      <div className="space-y-1">
        <label htmlFor="razon_social" className="text-sm font-medium">
          Razón social
        </label>
        <input
          id="razon_social"
          value={razonSocial}
          onChange={(event) => setRazonSocial(event.target.value)}
          required
          maxLength={200}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="contacto_nombre" className="text-sm font-medium">
            Contacto (nombre)
          </label>
          <input
            id="contacto_nombre"
            value={contactoNombre}
            onChange={(event) => setContactoNombre(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="contacto_telefono" className="text-sm font-medium">
            Teléfono
          </label>
          <input
            id="contacto_telefono"
            value={contactoTelefono}
            onChange={(event) => setContactoTelefono(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="contacto_correo" className="text-sm font-medium">
          Correo de contacto
        </label>
        <input
          id="contacto_correo"
          type="email"
          value={contactoCorreo}
          onChange={(event) => setContactoCorreo(event.target.value)}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
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
          onClick={() => router.push("/proveedores")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
