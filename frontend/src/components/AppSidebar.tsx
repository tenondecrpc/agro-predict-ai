import { Link, useRouterState } from "@tanstack/react-router";
import { Inbox, FilePlus2, ScanText, GitCompareArrows, Truck, BarChart3, Sprout } from "lucide-react";

const items = [
  { to: "/", label: "Inbox", icon: Inbox, exact: true },
  { to: "/nueva", label: "Nueva solicitud", icon: FilePlus2 },
  { to: "/cargar", label: "Cargar cotización", icon: ScanText },
  { to: "/comparar/pr-001", label: "Comparar y recomendar", icon: GitCompareArrows },
  { to: "/proveedores", label: "Proveedores", icon: Truck },
  { to: "/dashboard", label: "Dashboard ejecutivo", icon: BarChart3 },
];

export function AppSidebar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="sidebar-gradient w-64 shrink-0 hidden md:flex flex-col text-sidebar-foreground border-r border-sidebar-border min-h-screen">
      <div className="px-5 pt-6 pb-5 border-b border-sidebar-border/60">
        <div className="flex items-center gap-2.5">
          <div className="h-9 w-9 rounded-xl bg-sidebar-primary/20 ring-1 ring-sidebar-primary/40 flex items-center justify-center">
            <Sprout className="h-5 w-5 text-sidebar-primary" aria-hidden />
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight">AgroBuy</div>
            <div className="text-[11px] uppercase tracking-wider text-sidebar-foreground/60">Procurement Copilot</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {items.map((it) => {
          const active = it.exact ? pathname === it.to : pathname.startsWith(it.to.split("/").slice(0, 2).join("/"));
          const Icon = it.icon;
          return (
            <Link
              key={it.to}
              to={it.to}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring ${
                active
                  ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
                  : "text-sidebar-foreground/85 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              }`}
            >
              <Icon className="h-[18px] w-[18px]" aria-hidden />
              <span>{it.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-4 border-t border-sidebar-border/60 text-[11px] text-sidebar-foreground/65">
        <div className="font-semibold text-sidebar-foreground/85">Cooperativa Yguazú</div>
        <div>Itapúa · Campaña 2026/27</div>
      </div>
    </aside>
  );
}
