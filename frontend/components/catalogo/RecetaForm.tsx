"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearRecetaApiV1RecetasPost } from "@/lib/api/generated/endpoints/recetas/recetas";
import type { AlimentoListOut } from "@/lib/api/generated/model/alimentoListOut";
import type { RecetaIngredienteIn } from "@/lib/api/generated/model/recetaIngredienteIn";

/** El backend expone /catalogos/unidades-medida sin response_model (list[dict]). */
export type UnidadMedida = { unidad_id: number; codigo: string; nombre: string };

const CATEGORIAS = ["SOPA", "SEGUNDO", "ENTRADA", "BEBIDA", "POSTRE"];

function filaVacia(alimentoId: number, unidadId: number): RecetaIngredienteIn {
  return {
    alimento_id: alimentoId,
    cantidad_bruta_g: 0,
    cantidad_neta_g: 0,
    unidad_id: unidadId,
    factor_conversion: 1,
    merma_pct: 0,
  };
}

export function RecetaForm({
  alimentos,
  unidades,
}: {
  alimentos: AlimentoListOut[];
  unidades: UnidadMedida[];
}) {
  const router = useRouter();
  const crear = useCrearRecetaApiV1RecetasPost();

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [categoria, setCategoria] = useState(CATEGORIAS[0]);
  const [descripcion, setDescripcion] = useState("");
  const [numeroRaciones, setNumeroRaciones] = useState("");
  const [tamanoPorcion, setTamanoPorcion] = useState("");
  const [rendimiento, setRendimiento] = useState("");
  const [mermaEstimada, setMermaEstimada] = useState("0");
  const [procedimiento, setProcedimiento] = useState("");
  const [ingredientes, setIngredientes] = useState<RecetaIngredienteIn[]>([]);
  const [error, setError] = useState<string | null>(null);

  function agregarIngrediente() {
    if (alimentos.length === 0 || unidades.length === 0) return;
    setIngredientes((filas) => [
      ...filas,
      filaVacia(alimentos[0].alimento_id, unidades[0].unidad_id),
    ]);
  }

  function actualizarIngrediente(index: number, patch: Partial<RecetaIngredienteIn>) {
    setIngredientes((filas) =>
      filas.map((fila, i) => (i === index ? { ...fila, ...patch } : fila)),
    );
  }

  function quitarIngrediente(index: number) {
    setIngredientes((filas) => filas.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (ingredientes.length === 0) {
      setError("RN-23: la receta necesita al menos un ingrediente.");
      return;
    }

    const response = await crear.mutateAsync({
      data: {
        codigo,
        nombre,
        categoria_preparacion: categoria,
        descripcion: descripcion || null,
        numero_raciones_base: Number(numeroRaciones),
        tamano_porcion_g: Number(tamanoPorcion),
        rendimiento_pct: Number(rendimiento),
        merma_estimada_pct: Number(mermaEstimada),
        procedimiento: procedimiento || null,
        ingredientes,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/dosificacion/recetas/${response.data.receta_id}`);
    router.refresh();
  }

  if (alimentos.length === 0 || unidades.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un alimento del catálogo nutricional y una
        unidad de medida para crear una receta.
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
          <label htmlFor="codigo" className="text-sm font-medium">
            Código
          </label>
          <input
            id="codigo"
            value={codigo}
            onChange={(event) => setCodigo(event.target.value)}
            required
            maxLength={30}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
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

      <div className="space-y-1">
        <label htmlFor="categoria" className="text-sm font-medium">
          Categoría de preparación
        </label>
        <select
          id="categoria"
          value={categoria}
          onChange={(event) => setCategoria(event.target.value)}
          className="w-full max-w-xs rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        >
          {CATEGORIAS.map((opcion) => (
            <option key={opcion} value={opcion}>
              {opcion}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="space-y-1">
          <label htmlFor="numero_raciones" className="text-sm font-medium">
            N° raciones base
          </label>
          <input
            id="numero_raciones"
            type="number"
            min="1"
            value={numeroRaciones}
            onChange={(event) => setNumeroRaciones(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="tamano_porcion" className="text-sm font-medium">
            Porción (g)
          </label>
          <input
            id="tamano_porcion"
            type="number"
            min="0.01"
            step="0.01"
            value={tamanoPorcion}
            onChange={(event) => setTamanoPorcion(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="rendimiento" className="text-sm font-medium">
            Rendimiento (%)
          </label>
          <input
            id="rendimiento"
            type="number"
            min="0.01"
            max="100"
            step="0.01"
            value={rendimiento}
            onChange={(event) => setRendimiento(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="merma_estimada" className="text-sm font-medium">
            Merma estimada (%)
          </label>
          <input
            id="merma_estimada"
            type="number"
            min="0"
            max="100"
            step="0.01"
            value={mermaEstimada}
            onChange={(event) => setMermaEstimada(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <div className="space-y-1">
        <label htmlFor="descripcion" className="text-sm font-medium">
          Descripción (opcional)
        </label>
        <textarea
          id="descripcion"
          value={descripcion}
          onChange={(event) => setDescripcion(event.target.value)}
          rows={2}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="space-y-1">
        <label htmlFor="procedimiento" className="text-sm font-medium">
          Procedimiento (opcional)
        </label>
        <textarea
          id="procedimiento"
          value={procedimiento}
          onChange={(event) => setProcedimiento(event.target.value)}
          rows={3}
          className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">
            Ingredientes <span className="text-danger">*</span>
          </span>
          <button
            type="button"
            onClick={agregarIngrediente}
            className="text-sm text-primary hover:underline"
          >
            + Agregar ingrediente
          </button>
        </div>
        {ingredientes.length === 0 && (
          <p className="text-xs text-text-secondary">
            RN-23: se necesita al menos un ingrediente.
          </p>
        )}
        {ingredientes.map((fila, index) => (
          <div
            key={index}
            className="grid grid-cols-2 gap-2 rounded-md border border-border/20 p-3 sm:grid-cols-6 sm:items-end"
          >
            <div className="space-y-1 sm:col-span-2">
              <label className="text-xs text-text-secondary">Alimento</label>
              <select
                value={fila.alimento_id}
                onChange={(event) =>
                  actualizarIngrediente(index, { alimento_id: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              >
                {alimentos.map((alimento) => (
                  <option key={alimento.alimento_id} value={alimento.alimento_id}>
                    {alimento.codigo} — {alimento.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Cant. bruta (g)</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={fila.cantidad_bruta_g}
                onChange={(event) =>
                  actualizarIngrediente(index, {
                    cantidad_bruta_g: Number(event.target.value),
                  })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Cant. neta (g)</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={fila.cantidad_neta_g}
                onChange={(event) =>
                  actualizarIngrediente(index, {
                    cantidad_neta_g: Number(event.target.value),
                  })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-text-secondary">Unidad</label>
              <select
                value={fila.unidad_id}
                onChange={(event) =>
                  actualizarIngrediente(index, { unidad_id: Number(event.target.value) })
                }
                className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
              >
                {unidades.map((unidad) => (
                  <option key={unidad.unidad_id} value={unidad.unidad_id}>
                    {unidad.codigo}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => quitarIngrediente(index)}
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
          {crear.isPending ? "Creando..." : "Crear receta"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/dosificacion/recetas")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
