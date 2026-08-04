import { ModuleTabs } from "@/components/dosificacion/ModuleTabs";

export default function DosificacionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Dosificación nutricional
        </h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
