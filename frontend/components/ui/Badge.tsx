const VARIANT_STYLES = {
  primary: "bg-primary/10 text-primary",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  danger: "bg-danger/10 text-danger",
  neutral: "bg-neutral-dark/10 text-neutral-dark",
} as const;

export type BadgeVariant = keyof typeof VARIANT_STYLES;

export function Badge({
  label,
  variant = "neutral",
}: {
  label: string;
  variant?: BadgeVariant;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${VARIANT_STYLES[variant]}`}
    >
      {label}
    </span>
  );
}
