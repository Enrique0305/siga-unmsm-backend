import { SolicitudCocinaForm } from "@/components/cocina/SolicitudCocinaForm";
import { serverFetch } from "@/lib/api/server-fetch";
import type { CentroConsumoOut } from "@/lib/api/generated/model/centroConsumoOut";
import type { MenuDiaOut } from "@/lib/api/generated/model/menuDiaOut";
import type { PageMenuQuincenalOut } from "@/lib/api/generated/model/pageMenuQuincenalOut";
import type { PageProductoOut } from "@/lib/api/generated/model/pageProductoOut";

export default async function NuevaSolicitudCocinaPage() {
  const [centrosConsumo, menusQuincenales, productos] = await Promise.all([
    serverFetch<CentroConsumoOut[]>("/catalogos/centros-consumo"),
    serverFetch<PageMenuQuincenalOut>("/planificacion/menus-quincenales?page_size=100"),
    serverFetch<PageProductoOut>("/productos?page_size=100"),
  ]);

  const diasPorMenu = await Promise.all(
    menusQuincenales.items.map((menu) =>
      serverFetch<MenuDiaOut[]>(`/planificacion/menus-quincenales/${menu.menu_id}/dias`),
    ),
  );
  const menuDias = diasPorMenu.flat();

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-foreground">Nueva solicitud de cocina</h2>
      <SolicitudCocinaForm
        centrosConsumo={centrosConsumo}
        menuDias={menuDias}
        productos={productos.items}
      />
    </div>
  );
}
