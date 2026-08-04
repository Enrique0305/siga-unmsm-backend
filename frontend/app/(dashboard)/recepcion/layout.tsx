import { ModuleTabs } from "@/components/recepcion/ModuleTabs";

export default function RecepcionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Recepción y calidad</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
