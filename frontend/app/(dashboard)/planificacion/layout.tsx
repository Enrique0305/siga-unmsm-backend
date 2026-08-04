import { ModuleTabs } from "@/components/planificacion/ModuleTabs";

export default function PlanificacionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Planificación anual
        </h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
