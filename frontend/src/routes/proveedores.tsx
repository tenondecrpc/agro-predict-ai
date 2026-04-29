import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageShell } from "@/components/PageShell";
import { api } from "@/lib/api";
import { fmtPct, fmtNum, fmtDate } from "@/lib/format";
import { Truck, Award, FileText, Calendar } from "lucide-react";

export const Route = createFileRoute("/proveedores")({
  component: ProveedoresPage,
  head: () => ({ meta: [{ title: "Catálogo de proveedores — AgroBuy" }] }),
});

function ProveedoresPage() {
  const { data: suppliers = [] } = useQuery({ queryKey: ["suppliers"], queryFn: api.listSuppliers });

  return (
    <PageShell title="Catálogo de proveedores" subtitle={`${suppliers.length} proveedores activos`}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.map((s) => {
          const score = s.ml_p_on_time;
          const tone = score >= 0.85 ? "stroke-primary text-primary" : score >= 0.75 ? "stroke-warning text-warning-foreground" : "stroke-destructive text-destructive";
          const r = 28, c = 2 * Math.PI * r, off = c * (1 - score);
          return (
            <article key={s.id} className="card-soft p-5 hover:shadow-md transition-shadow">
              <header className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
                    <Truck className="h-3 w-3" aria-hidden /> RUC {s.ruc}
                  </div>
                  <h2 className="text-base font-bold leading-tight">{s.legal_name}</h2>
                </div>
                <div className="relative h-16 w-16 shrink-0">
                  <svg viewBox="0 0 70 70" className="h-16 w-16 -rotate-90">
                    <circle cx="35" cy="35" r={r} fill="none" stroke="var(--color-border)" strokeWidth="6" />
                    <circle cx="35" cy="35" r={r} fill="none" className={tone} strokeWidth="6" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-sm font-bold num">{Math.round(score * 100)}</span>
                    <span className="text-[8px] uppercase tracking-wider text-muted-foreground">on-time</span>
                  </div>
                </div>
              </header>

              <div className="mt-3 flex flex-wrap gap-1">
                {s.primary_categories.map((c) => (
                  <span key={c} className="inline-flex items-center rounded-full bg-primary-soft text-primary px-2 py-0.5 text-[11px] font-semibold capitalize">{c}</span>
                ))}
              </div>

              <dl className="mt-4 grid grid-cols-3 gap-2 text-center">
                <Stat icon={FileText} label="Cotizaciones" value={fmtNum(s.quotations_received)} />
                <Stat icon={Award} label="Adjudicaciones" value={fmtNum(s.awards)} />
                <Stat icon={Calendar} label="On-time hist." value={fmtPct(s.on_time_rate)} />
              </dl>

              <div className="mt-3 pt-3 border-t border-border text-[11px] text-muted-foreground">
                Última actividad: {fmtDate(s.last_activity)}
              </div>
            </article>
          );
        })}
      </div>
    </PageShell>
  );
}

function Stat({ icon: Icon, label, value }: { icon: typeof Truck; label: string; value: string }) {
  return (
    <div className="rounded-lg bg-muted/50 px-2 py-2">
      <Icon className="h-3.5 w-3.5 mx-auto text-muted-foreground" aria-hidden />
      <div className="mt-0.5 text-sm font-bold num">{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground leading-tight">{label}</div>
    </div>
  );
}
