import { ModuleTabs } from "@/components/almacenes/ModuleTabs";

export default function AlmacenesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Almacenes</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
