import { ModuleTabs } from "@/components/proveedores/ModuleTabs";

export default function ProveedoresLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Proveedores y contratos
        </h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
