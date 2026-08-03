const VARIANT_STYLES = {
  primary: "border-primary/20 bg-primary/5 text-primary",
  success: "border-success/20 bg-success/5 text-success",
  warning: "border-warning/20 bg-warning/5 text-warning",
  danger: "border-danger/20 bg-danger/5 text-danger",
  neutral: "border-neutral-dark/20 bg-neutral-dark/5 text-neutral-dark",
} as const;

export type StatCardVariant = keyof typeof VARIANT_STYLES;

export function StatCard({
  label,
  value,
  variant = "primary",
  hint,
}: {
  label: string;
  value: string;
  variant?: StatCardVariant;
  hint?: string;
}) {
  return (
    <div
      className={`rounded-lg border p-5 ${VARIANT_STYLES[variant]}`}
    >
      <p className="text-sm font-medium text-text-secondary">{label}</p>
      <p className="mt-2 text-3xl font-semibold">{value}</p>
      {hint && <p className="mt-1 text-xs text-text-secondary">{hint}</p>}
    </div>
  );
}
