"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ValorNutricionalFields } from "@/components/catalogo/ValorNutricionalFields";
import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearAlimentoApiV1AlimentosPost } from "@/lib/api/generated/endpoints/catálogo-nutricional/catálogo-nutricional";
import type { CategoriaAlimentoOut } from "@/lib/api/generated/model/categoriaAlimentoOut";
import type { ValorNutricional } from "@/lib/api/generated/model/valorNutricional";

const TIPOS = [
  { value: "BASE_TABLA", label: "Base de tabla" },
  { value: "PREPARADO_IMPORTADO", label: "Preparado importado" },
  { value: "PREPARACION_INSTITUCIONAL", label: "Preparación institucional" },
];

export function AlimentoForm({ categorias }: { categorias: CategoriaAlimentoOut[] }) {
  const router = useRouter();
  const crear = useCrearAlimentoApiV1AlimentosPost();

  const [codigo, setCodigo] = useState("");
  const [nombre, setNombre] = useState("");
  const [categoriaId, setCategoriaId] = useState<number | string>(
    categorias[0]?.categoria_alimento_id ?? "",
  );
  const [tipo, setTipo] = useState("PREPARACION_INSTITUCIONAL");
  const [fuente, setFuente] = useState("Registro institucional");
  const [valores, setValores] = useState<ValorNutricional>({});
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        codigo,
        nombre,
        categoria_alimento_id: Number(categoriaId),
        tipo,
        fuente,
        valores,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    router.push(`/dosificacion/${response.data.alimento_id}`);
    router.refresh();
  }

  if (categorias.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos una categoría de alimento para crear un
        registro nuevo.
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

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="space-y-1">
          <label htmlFor="categoria_id" className="text-sm font-medium">
            Categoría
          </label>
          <select
            id="categoria_id"
            value={categoriaId}
            onChange={(event) => setCategoriaId(event.target.value)}
            required
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {categorias.map((categoria) => (
              <option
                key={categoria.categoria_alimento_id}
                value={categoria.categoria_alimento_id}
              >
                {categoria.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="tipo" className="text-sm font-medium">
            Tipo
          </label>
          <select
            id="tipo"
            value={tipo}
            onChange={(event) => setTipo(event.target.value)}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            {TIPOS.map((opcion) => (
              <option key={opcion.value} value={opcion.value}>
                {opcion.label}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label htmlFor="fuente" className="text-sm font-medium">
            Fuente
          </label>
          <input
            id="fuente"
            value={fuente}
            onChange={(event) => setFuente(event.target.value)}
            maxLength={255}
            className="w-full rounded-md border border-border/30 px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>

      <ValorNutricionalFields
        values={valores}
        onChange={(patch) => setValores((prev) => ({ ...prev, ...patch }))}
      />

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={crear.isPending}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
        >
          {crear.isPending ? "Creando..." : "Crear alimento"}
        </button>
        <button
          type="button"
          onClick={() => router.push("/dosificacion")}
          className="rounded-md border border-border/30 px-4 py-2 text-sm text-foreground hover:bg-surface"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}
