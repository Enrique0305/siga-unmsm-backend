import type { ValorNutricional } from "@/lib/api/generated/model/valorNutricional";

type NutrienteKey = keyof ValorNutricional;

const GRUPOS: { titulo: string; campos: { key: NutrienteKey; label: string }[] }[] = [
  {
    titulo: "Energía",
    campos: [
      { key: "energia_kcal", label: "Energía (kcal)" },
      { key: "energia_kj", label: "Energía (kJ)" },
    ],
  },
  {
    titulo: "Macronutrientes",
    campos: [
      { key: "agua_g", label: "Agua (g)" },
      { key: "proteinas_g", label: "Proteínas (g)" },
      { key: "grasa_total_g", label: "Grasa total (g)" },
      { key: "carbohidratos_totales_g", label: "Carbohidratos totales (g)" },
      { key: "carbohidratos_disponibles_g", label: "Carbohidratos disponibles (g)" },
      { key: "fibra_dietaria_g", label: "Fibra dietaria (g)" },
      { key: "cenizas_g", label: "Cenizas (g)" },
    ],
  },
  {
    titulo: "Minerales",
    campos: [
      { key: "calcio_mg", label: "Calcio (mg)" },
      { key: "fosforo_mg", label: "Fósforo (mg)" },
      { key: "zinc_mg", label: "Zinc (mg)" },
      { key: "hierro_mg", label: "Hierro (mg)" },
      { key: "sodio_mg", label: "Sodio (mg)" },
      { key: "potasio_mg", label: "Potasio (mg)" },
    ],
  },
  {
    titulo: "Vitaminas",
    campos: [
      { key: "vitamina_a_ug", label: "Vitamina A (µg)" },
      { key: "tiamina_mg", label: "Tiamina (mg)" },
      { key: "riboflavina_mg", label: "Riboflavina (mg)" },
      { key: "niacina_mg", label: "Niacina (mg)" },
      { key: "vitamina_c_mg", label: "Vitamina C (mg)" },
      { key: "acido_folico_ug", label: "Ácido fólico (µg)" },
    ],
  },
];

export function ValorNutricionalFields({
  values,
  onChange,
}: {
  values: ValorNutricional;
  onChange: (patch: Partial<ValorNutricional>) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-xs text-text-secondary">
        Valores por 100 g de porción comestible. Todos son opcionales.
      </p>
      {GRUPOS.map((grupo) => (
        <fieldset key={grupo.titulo} className="space-y-2">
          <legend className="text-sm font-medium text-foreground">{grupo.titulo}</legend>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {grupo.campos.map((campo) => (
              <div key={campo.key} className="space-y-1">
                <label htmlFor={campo.key} className="text-xs text-text-secondary">
                  {campo.label}
                </label>
                <input
                  id={campo.key}
                  type="number"
                  step="0.01"
                  value={values[campo.key] ?? ""}
                  onChange={(event) =>
                    onChange({
                      [campo.key]:
                        event.target.value === "" ? null : Number(event.target.value),
                    })
                  }
                  className="w-full rounded-md border border-border/30 px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                />
              </div>
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
