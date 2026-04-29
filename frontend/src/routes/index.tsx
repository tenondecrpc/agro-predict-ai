import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { UrgencyPill, StatusPill } from "@/components/Pills";
import { api } from "@/lib/api";
import { fmtPYG, fmtNum, daysUntil } from "@/lib/format";
import type { PurchaseRequest } from "@/lib/types";
import {
  ChevronRight, Wheat, Sprout, Beaker, Wrench, Truck as TruckIcon, Fuel,
  TrendingUp, Wallet, AlertCircle, Timer, Plus, Search,
} from "lucide-react";

export const Route = createFileRoute("/")({
  component: InboxPage,
  head: () => ({
    meta: [
      { title: "Solicitudes activas — AgroBuy" },
      { name: "description", content: "Inbox de solicitudes de compra de Cooperativa Yguazú." },
    ],
  }),
});

const cropIcon: Record<string, typeof Sprout> = {
  soja: Sprout, maiz: Wheat, trigo: Wheat, sorgo: Wheat, girasol: Sprout, arroz: Wheat,
};
const catIcon = {
  fertilizante: Beaker, semilla: Sprout, fitosanitario: Beaker,
  maquinaria: Wrench, repuesto: Wrench, combustible: Fuel,
} as const;

function KpiCard({
  icon: Icon, label, value, sub, tone = "primary",
}: {
  icon: typeof Sprout; label: string; value: string; sub?: string; tone?: "primary" | "earth" | "warning" | "info";
}) {
  const toneMap = {
    primary: "bg-primary/10 text-primary ring-primary/20",
    earth: "bg-earth/10 text-earth ring-earth/20",
    warning: "bg-warning/15 text-warning-foreground ring-warning/30",
    info: "bg-info/10 text-info ring-info/20",
  };
  return (
    <div className="card-soft p-5">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">{label}</div>
          <div className="mt-2 text-2xl kpi-num text-foreground">{value}</div>
          {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
        </div>
        <div className={`h-10 w-10 rounded-xl ring-1 flex items-center justify-center ${toneMap[tone]}`}>
          <Icon className="h-5 w-5" aria-hidden />
        </div>
      </div>
    </div>
  );
}

function FilterPill({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-xs font-semibold ring-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active
          ? "bg-primary text-primary-foreground ring-primary"
          : "bg-card text-foreground ring-border hover:bg-accent"
      }`}
    >
      {children}
    </button>
  );
}

function InboxPage() {
  const { data: requests = [], isLoading } = useQuery({ queryKey: ["requests"], queryFn: api.listRequests });
  const [estado, setEstado] = useState<string>("todos");
  const [cultivo, setCultivo] = useState<string>("todos");
  const [search, setSearch] = useState("");

  const filtered = useMemo(
    () =>
      requests.filter((r) => {
        if (estado !== "todos" && r.status !== estado) return false;
        if (cultivo !== "todos" && r.target_crop !== cultivo) return false;
        if (search && !r.title.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
      }),
    [requests, estado, cultivo, search],
  );

  const kpis = useMemo(() => {
    const activas = requests.filter((r) => ["publicada", "en_evaluacion"].includes(r.status));
    const monto = activas.reduce((s, r) => s + r.budget_pyg, 0);
    const pendApr = requests.filter((r) => r.status === "en_evaluacion").length;
    return {
      activas: activas.length,
      monto,
      pendApr,
      cycle: 11,
    };
  }, [requests]);

  return (
    <PageShell title="Solicitudes activas">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">Inbox del comprador</span>
          <span className="inline-flex items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-bold px-2.5 py-0.5 ring-1 ring-primary/20 num">
            {requests.length}
          </span>
        </div>
        <Link
          to="/nueva"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Plus className="h-4 w-4" aria-hidden /> Nueva solicitud
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
        <KpiCard icon={TrendingUp} label="Solicitudes activas" value={fmtNum(kpis.activas)} sub="publicadas + en evaluación" />
        <KpiCard icon={Wallet} label="Monto en proceso" value={fmtPYG(kpis.monto)} sub="presupuesto agregado" tone="earth" />
        <KpiCard icon={AlertCircle} label="Pendientes de aprobación" value={fmtNum(kpis.pendApr)} sub="esperando decisión" tone="warning" />
        <KpiCard icon={Timer} label="Tiempo promedio de cierre" value={`${kpis.cycle} días`} sub="últimos 30 días" tone="info" />
      </div>

      <div className="card-soft p-4 mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar solicitud…"
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-background border border-input text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Buscar solicitud"
            />
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs font-semibold text-muted-foreground mr-1">Estado:</span>
            {[
              ["todos", "Todos"], ["publicada", "Publicada"], ["en_evaluacion", "En evaluación"], ["adjudicada", "Adjudicada"],
            ].map(([k, l]) => (
              <FilterPill key={k} active={estado === k} onClick={() => setEstado(k)}>{l}</FilterPill>
            ))}
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <span className="text-xs font-semibold text-muted-foreground mr-1">Cultivo:</span>
            {[
              ["todos", "Todos"], ["soja", "Soja"], ["maiz", "Maíz"], ["trigo", "Trigo"], ["sorgo", "Sorgo"],
            ].map(([k, l]) => (
              <FilterPill key={k} active={cultivo === k} onClick={() => setCultivo(k)}>{l}</FilterPill>
            ))}
          </div>
        </div>
      </div>

      {/* Wide: table. Narrow: cards. */}
      <div className="hidden lg:block card-soft overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/60 text-muted-foreground">
            <tr>
              <th className="text-left font-semibold px-4 py-3">Solicitud</th>
              <th className="text-left font-semibold px-4 py-3">Cultivo · Ventana</th>
              <th className="text-left font-semibold px-4 py-3">Urgencia</th>
              <th className="text-right font-semibold px-4 py-3">Plazo</th>
              <th className="text-right font-semibold px-4 py-3">Presupuesto</th>
              <th className="text-left font-semibold px-4 py-3">Estado</th>
              <th className="px-3 py-3" />
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">Cargando…</td></tr>
            )}
            {!isLoading && filtered.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">Sin resultados con esos filtros.</td></tr>
            )}
            {filtered.map((r) => <RequestRow key={r.id} r={r} />)}
          </tbody>
        </table>
      </div>

      <div className="lg:hidden space-y-3">
        {filtered.map((r) => <RequestCard key={r.id} r={r} />)}
      </div>
    </PageShell>
  );
}

function RequestRow({ r }: { r: PurchaseRequest }) {
  const Crop = cropIcon[r.target_crop] ?? Sprout;
  const Cat = catIcon[r.category];
  const days = daysUntil(r.deadline);
  return (
    <tr className="border-t border-border hover:bg-accent/50 transition-colors">
      <td className="px-4 py-3">
        <Link to="/solicitud/$id" params={{ id: r.id }} className="block">
          <div className="font-semibold text-foreground line-clamp-1">{r.title}</div>
          <div className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
            <Cat className="h-3 w-3" aria-hidden /> {r.category} · {r.id}
          </div>
        </Link>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5 text-foreground"><Crop className="h-4 w-4 text-primary" aria-hidden /> <span className="capitalize">{r.target_crop}</span></div>
        <div className="text-xs text-muted-foreground">{r.fenological_window}</div>
      </td>
      <td className="px-4 py-3"><UrgencyPill value={r.urgency} /></td>
      <td className="px-4 py-3 text-right num">
        <div className={`font-semibold ${days <= 7 ? "text-destructive" : days <= 14 ? "text-warning-foreground" : "text-foreground"}`}>{days}d</div>
        <div className="text-[11px] text-muted-foreground">{new Date(r.deadline).toLocaleDateString("es-PY")}</div>
      </td>
      <td className="px-4 py-3 text-right num font-semibold">{fmtPYG(r.budget_pyg)}</td>
      <td className="px-4 py-3"><StatusPill value={r.status} /></td>
      <td className="px-3 py-3 text-right">
        <Link to="/solicitud/$id" params={{ id: r.id }} className="inline-flex p-1.5 rounded-md hover:bg-primary/10 text-muted-foreground hover:text-primary" aria-label={`Abrir ${r.title}`}>
          <ChevronRight className="h-4 w-4" />
        </Link>
      </td>
    </tr>
  );
}

function RequestCard({ r }: { r: PurchaseRequest }) {
  const Crop = cropIcon[r.target_crop] ?? Sprout;
  return (
    <Link to="/solicitud/$id" params={{ id: r.id }} className="card-soft p-4 block hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold">{r.title}</div>
          <div className="text-xs text-muted-foreground mt-1 flex items-center gap-1.5">
            <Crop className="h-3 w-3" aria-hidden /> <span className="capitalize">{r.target_crop}</span> · {r.fenological_window}
          </div>
        </div>
        <UrgencyPill value={r.urgency} />
      </div>
      <div className="flex items-center justify-between mt-3 text-sm">
        <StatusPill value={r.status} />
        <span className="num font-semibold">{fmtPYG(r.budget_pyg)}</span>
      </div>
    </Link>
  );
}
