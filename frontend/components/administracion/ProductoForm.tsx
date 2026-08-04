"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import {
  useActualizarProductoApiV1ProductosProductoIdPatch,
  useCrearProductoApiV1ProductosPost,
} from "@/lib/api/generated/endpoints/productos-catálogo-logístico/productos-catálogo-logístico";
import type { ProductoOut } from "@/lib/api/generated/model/productoOut";

type UnidadOption = { unidad_id: number; codigo: string; nombre: string };

export function ProductoForm({
  mode,
  producto,
  unidades,
}: {
  mode: "create" | "edit";
  producto?: ProductoOut;
  unidades: UnidadOption[];
}) {
  const router = useRouter();
  const crear = useCrearProductoApiV1ProductosPost();
  const actualizar = useActualizarProductoApiV1ProductosProductoIdPatch();

  const [codigo, setCodigo] = useState(producto?.codigo ?? "");
  const [nombre, setNombre] = useState(producto?.nombre ?? "");
  const [categoria, setCategoria] = useState(producto?.categoria ?? "");
  const [unidadId, setUnidadId] = useState<number | string>(
    producto?.unidad.unidad_id ?? unidades[0]?.unidad_id ?? "",
  );
  const [alimentoId, setAlimentoId] = useState(
    producto?.alimento_id != null ? String(producto.alimento_id) : "",
  );
  const [perecible, setPerecible] = useState(producto?.perecible ?? false);
  const [diasVidaUtil, setDiasVidaUtil] = useState(
    producto?.dias_vida_util != null ? String(producto.dias_vida_util) : "",
  );
  const [stockMinimo, setStockMinimo] = useState(
    producto?.stock_minimo_referencial != null ? String(producto.stock_minimo_referencial) : "",
  );
  const [estado, setEstado] = useState(producto?.estado ?? "ACTIVO");
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
          categoria: categoria || null,
          unidad_id: Number(unidadId),
          alimento_id: alimentoId ? Number(alimentoId) : null,
          perecible,
          dias_vida_util: diasVidaUtil ? Number(diasVidaUtil) : null,
          stock_minimo_referencial: stockMinimo ? Number(stockMinimo) : null,
        },
      });
      if (response.status !== 201) {
        setError(extractErrorMessage(response.data));
        return;
      }
    } else if (producto) {
      const response = await actualizar.mutateAsync({
        productoId: producto.producto_id,
        data: {
          nombre,
          categoria: categoria || null,
          unidad_id: Number(unidadId),
          perecible,
          dias_vida_util: diasVidaUtil ? Number(diasVidaUtil) : null,
          stock_minimo_referencial: stockMinimo ? Number(stockMinimo) : null,
          estado,
        },
      });
      if (response.status !== 200) {
        setError(extractErrorMessage(response.data));
        return;
      }
    }

    router.push("/administracion/productos");
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
          <label htmlFor="codigo" className="text-sm font-medium">
            Código
          </label>
          <input
            id="codigo"
            value={codigo}
            onChange={(event) => setCodigo(event.target.value)}
            required
            maxLength={30}
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
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="categoria" className="text-sm font-medium">
            Categoría (opcional)
          </label>
          <input
            id="categoria"
            value={categoria}
            onChange={(event) => setCategoria(event.target.value)}
            maxLength={80}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="unidad_id" className="text-sm font-medium">
            Unidad de medida
          </label>
          <select
            id="unidad_id"
            value={unidadId}
            onChange={(event) => setUnidadId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {unidades.map((unidad) => (
              <option key={unidad.unidad_id} value={unidad.unidad_id}>
                {unidad.codigo} — {unidad.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      {mode === "create" && (
        <div className="space-y-1">
          <label htmlFor="alimento_id" className="text-sm font-medium">
            ID de alimento (opcional, puente al catálogo nutricional)
          </label>
          <input
            id="alimento_id"
            type="number"
            min="1"
            value={alimentoId}
            onChange={(event) => setAlimentoId(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="space-y-1">
          <label htmlFor="dias_vida_util" className="text-sm font-medium">
            Días de vida útil (opcional)
          </label>
          <input
            id="dias_vida_util"
            type="number"
            min="1"
            value={diasVidaUtil}
            onChange={(event) => setDiasVidaUtil(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="stock_minimo" className="text-sm font-medium">
            Stock mínimo referencial (opcional)
          </label>
          <input
            id="stock_minimo"
            type="number"
            min="0"
            step="0.01"
            value={stockMinimo}
            onChange={(event) => setStockMinimo(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={perecible}
          onChange={(event) => setPerecible(event.target.checked)}
        />
        Es perecible
      </label>

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
          onClick={() => router.push("/administracion/productos")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
