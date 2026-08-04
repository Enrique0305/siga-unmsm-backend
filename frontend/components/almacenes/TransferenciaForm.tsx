"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearTransferenciaApiV1TransferenciasPost } from "@/lib/api/generated/endpoints/transferencias-entre-almacenes/transferencias-entre-almacenes";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";
import type { TransferenciaAlmacenDetalleIn } from "@/lib/api/generated/model/transferenciaAlmacenDetalleIn";

function filaVacia(productoId: number): TransferenciaAlmacenDetalleIn {
  return { producto_id: productoId, cantidad_enviada: 0 };
}

export function TransferenciaForm({
  almacenes,
  productos,
}: {
  almacenes: AlmacenOut[];
  productos: ProductoOut[];
}) {
  const router = useRouter();
  const crear = useCrearTransferenciaApiV1TransferenciasPost();

  const [numeroTransferencia, setNumeroTransferencia] = useState("");
  const [almacenOrigenId, setAlmacenOrigenId] = useState<number | string>(
    almacenes[0]?.almacen_id ?? "",
  );
  const [almacenDestinoId, setAlmacenDestinoId] = useState<number | string>(
    almacenes[1]?.almacen_id ?? "",
  );
  const [detalle, setDetalle] = useState<TransferenciaAlmacenDetalleIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  function agregarLinea() {
    if (productos.length === 0) return;
    setDetalle((filas) => [...filas, filaVacia(productos[0].producto_id)]);
  }

  function actualizarLinea(index: number, patch: Partial<TransferenciaAlmacenDetalleIn>) {
    setDetalle((filas) => filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)));
  }

  function quitarLinea(index: number) {
    setDetalle((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (Number(almacenOrigenId) === Number(almacenDestinoId)) {
      setError("El almacén de origen y destino no pueden ser el mismo.");
      return;
    }
    if (detalle.length === 0) {
      setError("Se necesita al menos una línea de detalle.");
      return;
    }

    const response = await crear.mutateAsync({
      data: {
        numero_transferencia: numeroTransferencia,
        almacen_origen_id: Number(almacenOrigenId),
        almacen_destino_id: Number(almacenDestinoId),
        detalle,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/almacenes/transferencias/${response.data.transferencia_id}`);
    router.refresh();
  }

  if (almacenes.length < 2 || productos.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesitan al menos 2 almacenes y un producto para registrar una
        transferencia.
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

      <div className="space-y-1">
        <label htmlFor="numero_transferencia" className="text-sm font-medium">
          N° de transferencia
        </label>
        <input
          id="numero_transferencia"
          value={numeroTransferencia}
          onChange={(event) => setNumeroTransferencia(event.target.value)}
          required
          maxLength={40}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="almacen_origen_id" className="text-sm font-medium">
            Almacén origen
          </label>
          <select
            id="almacen_origen_id"
            value={almacenOrigenId}
            onChange={(event) => setAlmacenOrigenId(event.target.value)}
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
          <label htmlFor="almacen_destino_id" className="text-sm font-medium">
            Almacén destino
          </label>
          <select
            id="almacen_destino_id"
            value={almacenDestinoId}
            onChange={(event) => setAlmacenDestinoId(event.target.value)}
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
              <label className="text-xs text-text-secondary">Cant. enviada</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={fila.cantidad_enviada}
                onChange={(event) =>
                  actualizarLinea(index, { cantidad_enviada: Number(event.target.value) })
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
          {crear.isPending ? "Registrando..." : "Registrar transferencia"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/almacenes/transferencias")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
