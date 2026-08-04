"use client";

import Link from "next/link";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearDevolucionAlmacenApiV1DevolucionesPost } from "@/lib/api/generated/endpoints/ajustes-mermas-y-devoluciones/ajustes-mermas-y-devoluciones";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";

export function DevolucionForm({
  almacenes,
  productos,
}: {
  almacenes: AlmacenOut[];
  productos: ProductoOut[];
}) {
  const crear = useCrearDevolucionAlmacenApiV1DevolucionesPost();

  const [almacenId, setAlmacenId] = useState<number | string>(almacenes[0]?.almacen_id ?? "");
  const [productoId, setProductoId] = useState<number | string>(productos[0]?.producto_id ?? "");
  const [tipo, setTipo] = useState("A_PROVEEDOR");
  const [cantidad, setCantidad] = useState("");
  const [motivo, setMotivo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState<{ almacenId: number; productoId: number } | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setExito(null);

    const response = await crear.mutateAsync({
      data: {
        almacen_id: Number(almacenId),
        producto_id: Number(productoId),
        tipo,
        cantidad: Number(cantidad),
        motivo: motivo || null,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setExito({ almacenId: Number(almacenId), productoId: Number(productoId) });
    setCantidad("");
    setMotivo("");
  }

  if (almacenes.length === 0 || productos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un almacén y un producto para registrar una devolución.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-lg border border-border/20 bg-white p-4"
    >
      <p className="text-sm font-medium text-foreground">Devolución</p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      {exito && (
        <p className="rounded-md bg-success/10 px-3 py-2 text-sm text-success">
          Devolución registrada.{" "}
          <Link
            href={`/almacenes/stock?almacen_id=${exito.almacenId}&producto_id=${exito.productoId}`}
            className="underline"
          >
            Ver stock actualizado
          </Link>
        </p>
      )}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-5 sm:items-end">
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Almacén</label>
          <select
            value={almacenId}
            onChange={(event) => setAlmacenId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          >
            {almacenes.map((a) => (
              <option key={a.almacen_id} value={a.almacen_id}>
                {a.codigo}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Producto</label>
          <select
            value={productoId}
            onChange={(event) => setProductoId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          >
            {productos.map((p) => (
              <option key={p.producto_id} value={p.producto_id}>
                {p.codigo} — {p.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Tipo</label>
          <select
            value={tipo}
            onChange={(event) => setTipo(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          >
            <option value="A_PROVEEDOR">A proveedor (resta stock)</option>
            <option value="DESDE_COCINA">Desde cocina (suma stock)</option>
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Cantidad</label>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={cantidad}
            onChange={(event) => setCantidad(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Motivo (opcional)</label>
          <input
            value={motivo}
            onChange={(event) => setMotivo(event.target.value)}
            maxLength={255}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={crear.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {crear.isPending ? "Registrando..." : "Registrar devolución"}
      </button>
    </form>
  );
}
