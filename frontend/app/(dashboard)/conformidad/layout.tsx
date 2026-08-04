import { ModuleTabs } from "@/components/conformidad/ModuleTabs";

export default function ConformidadLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Conformidad y pagos</h1>
        <ModuleTabs />
      </div>
      {children}
    </div>
  );
}
