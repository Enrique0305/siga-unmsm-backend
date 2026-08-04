"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useAgregarProductoContratadoApiV1ContratosContratoIdProductosPost } from "@/lib/api/generated/endpoints/contratos/contratos";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";

export function AgregarProductoContratadoForm({
  contratoId,
  productos,
}: {
  contratoId: number;
  productos: ProductoOut[];
}) {
  const router = useRouter();
  const agregar = useAgregarProductoContratadoApiV1ContratosContratoIdProductosPost();

  const [productoId, setProductoId] = useState<number | string>(
    productos[0]?.producto_id ?? "",
  );
  const [precioUnitario, setPrecioUnitario] = useState("");
  const [cantidadContratada, setCantidadContratada] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await agregar.mutateAsync({
      contratoId,
      data: {
        producto_id: Number(productoId),
        precio_unitario: Number(precioUnitario),
        cantidad_contratada: Number(cantidadContratada),
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setPrecioUnitario("");
    setCantidadContratada("");
    router.refresh();
  }

  if (productos.length === 0) {
    return (
      <p className="text-sm text-text-secondary">
        No hay productos en el catálogo logístico todavía.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
        <div className="space-y-1 sm:col-span-2">
          <label htmlFor="producto_id" className="text-sm font-medium">
            Producto
          </label>
          <select
            id="producto_id"
            value={productoId}
            onChange={(event) => setProductoId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {productos.map((producto) => (
              <option key={producto.producto_id} value={producto.producto_id}>
                {producto.codigo} — {producto.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="precio_unitario" className="text-sm font-medium">
            Precio unitario
          </label>
          <input
            id="precio_unitario"
            type="number"
            min="0.01"
            step="0.01"
            value={precioUnitario}
            onChange={(event) => setPrecioUnitario(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="cantidad_contratada" className="text-sm font-medium">
            Cantidad
          </label>
          <input
            id="cantidad_contratada"
            type="number"
            min="0.01"
            step="0.01"
            value={cantidadContratada}
            onChange={(event) => setCantidadContratada(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <button
        type="submit"
        disabled={agregar.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {agregar.isPending ? "Agregando..." : "Agregar producto"}
      </button>
    </form>
  );
}
