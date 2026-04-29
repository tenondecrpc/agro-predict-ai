import { Link, useRouterState } from "@tanstack/react-router";
import {
  Inbox,
  PlusCircle,
  FileText,
  Upload,
  Sparkles,
  Building2,
  LineChart,
  Sprout,
} from "lucide-react";

const HERO_ID = "req-urea-2627";

const NAV = [
  { kind: "static", to: "/", label: "Inbox", icon: Inbox, exact: true },
  { kind: "static", to: "/nueva", label: "Nueva solicitud", icon: PlusCircle },
  {
    kind: "param",
    to: "/solicitud/$id" as const,
    params: { id: HERO_ID },
    matchPrefix: "/solicitud",
    label: "Detalle (urea)",
    icon: FileText,
  },
  {
    kind: "param",
    to: "/cargar/$id" as const,
    params: { id: HERO_ID },
    matchPrefix: "/cargar",
    label: "Cargar cotización",
    icon: Upload,
  },
  {
    kind: "param",
    to: "/comparar/$id" as const,
    params: { id: HERO_ID },
    matchPrefix: "/comparar",
    label: "Comparar y recomendar",
    icon: Sparkles,
    hero: true,
  },
  { kind: "static", to: "/proveedores", label: "Proveedores", icon: Building2 },
  { kind: "static", to: "/dashboard", label: "Dashboard", icon: LineChart },
] as const;

export function Sidebar() {
  const path = useRouterState({ select: (s) => s.location.pathname });

  return (
    <aside className="sidebar-texture text-sidebar-foreground hidden md:flex md:flex-col w-64 shrink-0 border-r border-sidebar-border">
      <div className="px-5 py-6 flex items-center gap-3 border-b border-sidebar-border/50">
        <div className="size-10 rounded-xl bg-primary-glow/20 ring-1 ring-primary-glow/40 flex items-center justify-center">
          <Sprout className="size-5 text-primary-glow" aria-hidden />
        </div>
        <div>
          <div className="text-base font-bold tracking-tight">AgroBuy</div>
          <div className="text-[11px] uppercase tracking-wider text-sidebar-foreground/70">
            Procurement copilot
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1" aria-label="Navegación principal">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active =
            item.kind === "static"
              ? "exact" in item && item.exact
                ? path === item.to
                : path.startsWith(item.to)
              : path.startsWith(item.matchPrefix);

          const cls = [
            "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
            active
              ? "bg-sidebar-accent text-sidebar-accent-foreground shadow-soft"
              : "text-sidebar-foreground/85 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
          ].join(" ");

          const inner = (
            <>
              <Icon className="size-4 shrink-0" aria-hidden />
              <span className="truncate">{item.label}</span>
              {"hero" in item && item.hero && (
                <span className="ml-auto text-[10px] font-semibold text-primary-glow">★</span>
              )}
            </>
          );

          if (item.kind === "static") {
            return (
              <Link key={item.to} to={item.to} className={cls}>
                {inner}
              </Link>
            );
          }
          return (
            <Link key={item.to} to={item.to} params={item.params} className={cls}>
              {inner}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-sidebar-border/50 text-[11px] text-sidebar-foreground/70">
        Campaña <span className="text-sidebar-foreground font-semibold">2026/27</span> · v0.9
      </div>
    </aside>
  );
}
