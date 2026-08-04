import { ModuleTabs } from "@/components/compras/ModuleTabs";

export default function ComprasLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Compras</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
