import { ModuleTabs } from "@/components/administracion/ModuleTabs";

export default function AdministracionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Administración</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
