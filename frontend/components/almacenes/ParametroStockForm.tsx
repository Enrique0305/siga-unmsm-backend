"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useUpsertParametroApiV1ParametrosStockPut } from "@/lib/api/generated/endpoints/parámetros-de-stock-por-almacén/parámetros-de-stock-por-almacén";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";

export function ParametroStockForm({
  almacenes,
  productos,
}: {
  almacenes: AlmacenOut[];
  productos: ProductoOut[];
}) {
  const router = useRouter();
  const upsert = useUpsertParametroApiV1ParametrosStockPut();

  const [almacenId, setAlmacenId] = useState<number | string>(almacenes[0]?.almacen_id ?? "");
  const [productoId, setProductoId] = useState<number | string>(productos[0]?.producto_id ?? "");
  const [stockMinimo, setStockMinimo] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await upsert.mutateAsync({
      data: {
        almacen_id: Number(almacenId),
        producto_id: Number(productoId),
        stock_minimo: Number(stockMinimo),
      },
    });

    if (response.status !== 200) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setStockMinimo("");
    router.refresh();
  }

  if (almacenes.length === 0 || productos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un almacén y un producto para fijar un parámetro.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-lg border border-border/20 bg-white p-4"
    >
      <p className="text-sm font-medium text-foreground">Fijar parámetro de stock mínimo</p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:items-end">
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Almacén</label>
          <select
            value={almacenId}
            onChange={(event) => setAlmacenId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          >
            {almacenes.map((almacen) => (
              <option key={almacen.almacen_id} value={almacen.almacen_id}>
                {almacen.codigo} — {almacen.nombre}
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
            {productos.map((producto) => (
              <option key={producto.producto_id} value={producto.producto_id}>
                {producto.codigo} — {producto.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Stock mínimo (este almacén)</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            value={stockMinimo}
            onChange={(event) => setStockMinimo(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <p className="text-xs text-text-secondary">
        Sobreescribe, solo para este almacén, el stock mínimo referencial del producto usado en
        las alertas de stock bajo.
      </p>
      <button
        type="submit"
        disabled={upsert.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {upsert.isPending ? "Guardando..." : "Guardar parámetro"}
      </button>
    </form>
  );
}
