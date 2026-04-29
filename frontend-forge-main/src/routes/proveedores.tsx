import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Pill } from "@/components/agro/Pill";
import { SUPPLIERS } from "@/lib/agro/mock";
import { fmtPct } from "@/lib/agro/format";
import { Building2, CheckCircle2 } from "lucide-react";

export const Route = createFileRoute("/proveedores")({
  head: () => ({
    meta: [
      { title: "Proveedores · AgroBuy" },
      { name: "description", content: "Catálogo de proveedores certificados." },
    ],
  }),
  component: ProveedoresPage,
});

function ProveedoresPage() {
  return (
    <AppShell>
      <div className="mb-5">
        <h2 className="text-xl font-bold tracking-tight text-foreground">Catálogo de proveedores</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {SUPPLIERS.length} proveedores activos · ordenados por confianza ML
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...SUPPLIERS]
          .sort((a, b) => b.ml_p_on_time - a.ml_p_on_time)
          .map((s) => (
            <Card key={s.id} className="p-5 hover:shadow-card transition-shadow">
              <div className="flex items-start gap-3">
                <div className="size-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
                  <Building2 className="size-5" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-foreground truncate">{s.legal_name}</div>
                  <div className="text-xs text-muted-foreground">RUC {s.ruc}</div>
                </div>
                <MlCircle value={s.ml_p_on_time} />
              </div>

              <div className="mt-3 flex flex-wrap gap-1.5">
                {s.primary_categories.map((c) => (
                  <Pill key={c} tone="earth">{c}</Pill>
                ))}
              </div>

              <div className="grid grid-cols-3 gap-2 mt-4">
                <Stat label="On-time" value={fmtPct(s.on_time_rate)} />
                <Stat label="Cotizaciones" value={s.quotations_received} />
                <Stat label="Adjudicaciones" value={s.awards} />
              </div>

              <div className="mt-3 pt-3 border-t border-border flex items-center justify-between text-xs">
                <span className="text-muted-foreground">
                  Activo {new Date(s.last_activity).toLocaleDateString("es-PY")}
                </span>
                <span className="inline-flex items-center gap-1 text-success font-semibold">
                  <CheckCircle2 className="size-3.5" aria-hidden /> Verificado
                </span>
              </div>
            </Card>
          ))}
      </div>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-secondary/50 px-2.5 py-2">
      <div className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">{label}</div>
      <div className="text-sm font-bold tabular text-foreground mt-0.5">{value}</div>
    </div>
  );
}

function MlCircle({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const r = 18;
  const c = 2 * Math.PI * r;
  const offset = c - value * c;
  const color = pct >= 80 ? "text-success" : pct >= 60 ? "text-warning" : "text-destructive";
  return (
    <div className={`relative size-12 ${color}`} role="img" aria-label={`Confianza ML ${pct}%`}>
      <svg viewBox="0 0 50 50" className="size-12 -rotate-90">
        <circle cx="25" cy="25" r={r} stroke="currentColor" strokeOpacity="0.2" strokeWidth="5" fill="none" />
        <circle
          cx="25"
          cy="25"
          r={r}
          stroke="currentColor"
          strokeWidth="5"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[11px] font-bold tabular text-foreground">
        {pct}
      </div>
    </div>
  );
}
