import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Kpi } from "@/components/agro/Kpi";
import { Pill } from "@/components/agro/Pill";
import { CropIcon, StatusPill, UrgencyPill } from "@/components/agro/agro-pills";
import { REQUESTS } from "@/lib/agro/mock";
import { daysUntil, fmtPYG } from "@/lib/agro/format";
import {
  ArrowRight,
  Briefcase,
  CheckSquare,
  Clock,
  FileText,
  Search,
} from "lucide-react";
import { useMemo, useState } from "react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Inbox · AgroBuy" },
      { name: "description", content: "Solicitudes activas de compras agrícolas." },
    ],
  }),
  component: InboxPage,
});

const FENO = ["soja", "maiz", "trigo", "sorgo"] as const;

function InboxPage() {
  const [crop, setCrop] = useState<string>("todos");
  const [urgency, setUrgency] = useState<string>("todas");
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    return REQUESTS.filter((r) => {
      if (crop !== "todos" && r.crop !== crop) return false;
      if (urgency !== "todas" && r.urgency !== urgency) return false;
      if (q && !r.title.toLowerCase().includes(q.toLowerCase())) return false;
      return true;
    });
  }, [crop, urgency, q]);

  const kpis = useMemo(() => {
    const monto = REQUESTS.filter((r) => r.status !== "cerrada").reduce(
      (s, r) => s + r.total_estimated_pyg,
      0,
    );
    return {
      activas: REQUESTS.filter((r) => r.status !== "cerrada" && r.status !== "borrador").length,
      monto,
      pendientes: REQUESTS.filter((r) => r.status === "recomendada").length || 1,
      avgDias: 8.4,
    };
  }, []);

  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-5">
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Solicitudes activas
        </h2>
        <span className="inline-flex items-center justify-center min-w-7 h-6 px-2 rounded-full bg-primary text-primary-foreground text-xs font-bold">
          {kpis.activas}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Kpi
          label="Solicitudes activas"
          value={kpis.activas}
          sub="abiertas y en cotización"
          icon={<Briefcase className="size-5" aria-hidden />}
          tone="primary"
        />
        <Kpi
          label="Monto en proceso"
          value={fmtPYG(kpis.monto)}
          sub="estimado total"
          icon={<FileText className="size-5" aria-hidden />}
          tone="earth"
        />
        <Kpi
          label="Pendientes de aprobación"
          value={kpis.pendientes}
          sub="esperando director"
          icon={<CheckSquare className="size-5" aria-hidden />}
          tone="warning"
        />
        <Kpi
          label="Tiempo promedio de cierre"
          value={`${kpis.avgDias} días`}
          sub="últimos 90 días"
          icon={<Clock className="size-5" aria-hidden />}
          tone="info"
        />
      </div>

      <Card className="p-4 mb-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por título…"
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-background border border-input text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              aria-label="Buscar solicitudes"
            />
          </div>
          <FilterPills
            label="Cultivo"
            value={crop}
            onChange={setCrop}
            options={[{ v: "todos", l: "Todos" }, ...FENO.map((c) => ({ v: c, l: c }))]}
          />
          <FilterPills
            label="Urgencia"
            value={urgency}
            onChange={setUrgency}
            options={[
              { v: "todas", l: "Todas" },
              { v: "baja", l: "Baja" },
              { v: "media", l: "Media" },
              { v: "alta", l: "Alta" },
              { v: "critica", l: "Crítica" },
            ]}
          />
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="hidden md:grid grid-cols-[2fr_120px_140px_120px_110px_180px_140px_40px] gap-3 px-5 py-3 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-muted-foreground bg-secondary/40">
          <div>Solicitud</div>
          <div>Cultivo</div>
          <div>Ventana</div>
          <div>Urgencia</div>
          <div>Plazo</div>
          <div className="text-right">Total estimado</div>
          <div>Estado</div>
          <div></div>
        </div>
        <ul className="divide-y divide-border">
          {filtered.map((r) => {
            const days = daysUntil(r.deadline);
            return (
              <li key={r.id}>
                <Link
                  to="/solicitud/$id"
                  params={{ id: r.id }}
                  className="grid md:grid-cols-[2fr_120px_140px_120px_110px_180px_140px_40px] grid-cols-1 gap-3 px-5 py-4 items-center hover:bg-secondary/40 transition-colors"
                >
                  <div className="min-w-0">
                    <div className="font-semibold text-foreground truncate">{r.title}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {r.department} · zafra {r.zafra}
                    </div>
                  </div>
                  <CropIcon value={r.crop} />
                  <Pill tone="earth">{r.fenological_window}</Pill>
                  <UrgencyPill value={r.urgency} />
                  <div className="text-sm tabular text-foreground">
                    {days > 0 ? `${days} días` : "Vencido"}
                  </div>
                  <div className="text-right font-semibold tabular text-foreground">
                    {fmtPYG(r.total_estimated_pyg)}
                  </div>
                  <StatusPill value={r.status} />
                  <ArrowRight className="size-4 text-muted-foreground justify-self-end" aria-hidden />
                </Link>
              </li>
            );
          })}
        </ul>
      </Card>
    </AppShell>
  );
}

function FilterPills({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { v: string; l: string }[];
}) {
  return (
    <div className="flex items-center gap-1">
      <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mr-1">
        {label}
      </span>
      {options.map((o) => (
        <button
          key={o.v}
          type="button"
          onClick={() => onChange(o.v)}
          className={[
            "rounded-full px-3 py-1 text-xs font-semibold border transition-colors capitalize",
            value === o.v
              ? "bg-primary text-primary-foreground border-primary"
              : "bg-card text-foreground border-border hover:border-primary/40",
          ].join(" ")}
          aria-pressed={value === o.v}
        >
          {o.l}
        </button>
      ))}
    </div>
  );
}
