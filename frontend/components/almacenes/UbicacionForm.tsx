"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { extractErrorMessage } from "@/lib/api/errors";
import { useCrearUbicacionApiV1UbicacionesPost } from "@/lib/api/generated/endpoints/ubicaciones-internas/ubicaciones-internas";
import type { AlmacenOut } from "@/lib/api/generated/model/almacenOut";

export function UbicacionForm({ almacenes }: { almacenes: AlmacenOut[] }) {
  const router = useRouter();
  const crear = useCrearUbicacionApiV1UbicacionesPost();

  const [almacenId, setAlmacenId] = useState<number | string>(almacenes[0]?.almacen_id ?? "");
  const [zona, setZona] = useState("");
  const [estante, setEstante] = useState("");
  const [nivel, setNivel] = useState("");
  const [contenedorCamara, setContenedorCamara] = useState("");
  const [esCadenaFrio, setEsCadenaFrio] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const response = await crear.mutateAsync({
      data: {
        almacen_id: Number(almacenId),
        zona,
        estante: estante || null,
        nivel: nivel || null,
        contenedor_camara: contenedorCamara || null,
        es_cadena_frio: esCadenaFrio,
      },
    });

    if (response.status !== 201) {
      setError(extractErrorMessage(response.data));
      return;
    }

    setZona("");
    setEstante("");
    setNivel("");
    setContenedorCamara("");
    setEsCadenaFrio(false);
    router.refresh();
  }

  if (almacenes.length === 0) {
    return (
      <p className="rounded-md bg-warning/10 px-4 py-3 text-sm text-warning">
        Se necesita al menos un almacén para crear una ubicación.
      </p>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-3 rounded-lg border border-border/20 bg-white p-4"
    >
      <p className="text-sm font-medium text-foreground">Nueva ubicación</p>
      {error && (
        <p className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">{error}</p>
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
            {almacenes.map((almacen) => (
              <option key={almacen.almacen_id} value={almacen.almacen_id}>
                {almacen.codigo} — {almacen.nombre}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Zona</label>
          <input
            value={zona}
            onChange={(event) => setZona(event.target.value)}
            required
            maxLength={60}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Estante (opcional)</label>
          <input
            value={estante}
            onChange={(event) => setEstante(event.target.value)}
            maxLength={60}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Nivel (opcional)</label>
          <input
            value={nivel}
            onChange={(event) => setNivel(event.target.value)}
            maxLength={60}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-text-secondary">Contenedor/cámara (opcional)</label>
          <input
            value={contenedorCamara}
            onChange={(event) => setContenedorCamara(event.target.value)}
            maxLength={60}
            className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
          />
        </div>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={esCadenaFrio}
          onChange={(event) => setEsCadenaFrio(event.target.checked)}
        />
        Cadena de frío
      </label>
      <button
        type="submit"
        disabled={crear.isPending}
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-60"
      >
        {crear.isPending ? "Creando..." : "Crear ubicación"}
      </button>
    </form>
  );
}
