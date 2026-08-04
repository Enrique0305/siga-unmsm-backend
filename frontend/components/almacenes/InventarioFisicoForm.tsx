"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearInventarioFisicoApiV1InventariosFisicosPost } from "@/lib/api/generated/endpoints/inventario-físico/inventario-físico";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { InventarioFisicoDetalleIn } from "@/lib/api/generated/model/inventarioFisicoDetalleIn";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";

function filaVacia(productoId: number): InventarioFisicoDetalleIn {
  return { producto_id: productoId, stock_contado: 0 };
}

export function InventarioFisicoForm({
  almacenes,
  productos,
}: {
  almacenes: AlmacenOut[];
  productos: ProductoOut[];
}) {
  const router = useRouter();
  const crear = useCrearInventarioFisicoApiV1InventariosFisicosPost();

  const [almacenId, setAlmacenId] = useState<number | string>(almacenes[0]?.almacen_id ?? "");
  const [fechaConteo, setFechaConteo] = useState("");
  const [detalle, setDetalle] = useState<InventarioFisicoDetalleIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  function agregarLinea() {
    if (productos.length === 0) return;
    setDetalle((filas) => [...filas, filaVacia(productos[0].producto_id)]);
  }

  function actualizarLinea(index: number, patch: Partial<InventarioFisicoDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  function quitarLinea(index: number) {
    setDetalle((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (detalle.length === 0) {
      setError("Se necesita al menos una línea de conteo.");
      return;
    }

    const response = await crear.mutateAsync({
      data: {
        almacen_id: Number(almacenId),
        fecha_conteo: fechaConteo,
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/almacenes/inventarios/${response.data.inventario_fisico_id}`);
    router.refresh();
  }

  if (almacenes.length === 0 || productos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un almacén y un producto para registrar un
        inventario físico.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="max-w-3xl space-y-4 rounded-lg border border-border/20 bg-white p-6"
    >
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="almacen_id" className="text-sm font-medium">
            Almacén
          </label>
          <select
            id="almacen_id"
            value={almacenId}
            onChange={(event) => setAlmacenId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {almacenes.map((a) => (
              <option key={a.almacen_id} value={a.almacen_id}>
                {a.codigo} — {a.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="fecha_conteo" className="text-sm font-medium">
            Fecha de conteo
          </label>
          <input
            id="fecha_conteo"
            type="date"
            value={fechaConteo}
            onChange={(event) => setFechaConteo(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            Detalle <span className="text-danger">*</span>
          </span>
          <button
            type="button"
            onClick={agregarLinea}
            className="text-sm text-primary hover:underline"
          >
            + Agregar línea
          </button>
        </div>
        {detalle.length === 0 && (
          <p className="text-xs text-text-secondary">Se necesita al menos una línea.</p>
        )}
        {detalle.map((fila, index) => (
          <div
            key={index}
            className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-4 sm:items-end"
          >
            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs text-text-secondary">Producto</label>
              <select
                value={fila.producto_id}
                onChange={(event) =>
                  actualizarLinea(index, { producto_id: Number(event.target.value) })
                }
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
              <label className="text-xs text-text-secondary">Stock contado</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={fila.stock_contado}
                onChange={(event) =>
                  actualizarLinea(index, { stock_contado: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
            <button
              type="button"
              onClick={() => quitarLinea(index)}
              className="text-sm text-danger hover:underline"
            >
              Quitar
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Registrando..." : "Registrar inventario físico"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/almacenes/inventarios")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
