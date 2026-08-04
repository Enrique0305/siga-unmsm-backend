import { ModuleTabs } from "@/components/reportes/ModuleTabs";

export default function ReportesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Reportes y auditoría</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
