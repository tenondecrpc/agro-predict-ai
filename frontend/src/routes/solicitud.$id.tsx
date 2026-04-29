import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageShell } from "@/components/PageShell";
import { api } from "@/lib/api";
import { fmtPYG, fmtNum, fmtDate, daysUntil } from "@/lib/format";
import { UrgencyPill, StatusPill, MLBand } from "@/components/Pills";
import { AlertTriangle, Upload, GitCompareArrows, Sparkles, Sprout, Calendar, MapPin, Wallet } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/solicitud/$id")({
  component: DetallePage,
  head: () => ({ meta: [{ title: "Detalle de solicitud — AgroBuy" }] }),
  errorComponent: ({ error, reset }) => {
    const router = useRouter();
    return (
      <PageShell title="Error">
        <div className="card-soft p-6">
          <p className="text-destructive">{error.message}</p>
          <button onClick={() => { router.invalidate(); reset(); }} className="mt-3 px-3 py-1.5 rounded bg-primary text-primary-foreground text-sm">Reintentar</button>
        </div>
      </PageShell>
    );
  },
  notFoundComponent: () => (
    <PageShell title="No encontrada"><div className="card-soft p-6">Solicitud no encontrada.</div></PageShell>
  ),
});

function DetallePage() {
  const { id } = Route.useParams();
  const { data: req } = useQuery({ queryKey: ["request", id], queryFn: () => api.getRequest(id) });
  const { data: quotes = [] } = useQuery({ queryKey: ["quotes", id], queryFn: () => api.listQuotations(id) });
  const [hover, setHover] = useState<string | null>(null);

  if (!req) return <PageShell title="Cargando…"><div /></PageShell>;
  const validated = quotes.length;
  const days = daysUntil(req.deadline);

  return (
    <PageShell title={req.title} subtitle={`${req.id} · creada ${fmtDate(req.created_at)} · ${req.created_by}`}>
      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6 pb-24">
        {/* LEFT */}
        <div className="xl:col-span-2 space-y-5">
          <section className="card-soft p-5">
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <StatusPill value={req.status} />
                <UrgencyPill value={req.urgency} />
              </div>
            </div>

            {req.description && <p className="text-sm text-foreground/85 mb-4">{req.description}</p>}

            <dl className="grid grid-cols-2 gap-3 text-sm">
              <Stat icon={Sprout} label="Cultivo" value={`${req.target_crop} · ${req.zafra}`} />
              <Stat icon={Calendar} label="Ventana fenológica" value={req.fenological_window} />
              <Stat icon={MapPin} label="Departamento" value={req.department} />
              <Stat icon={Calendar} label="Fecha límite" value={`${fmtDate(req.deadline)} (${days}d)`} highlight={days <= 7} />
              <Stat icon={Wallet} label="Presupuesto" value={fmtPYG(req.budget_pyg)} />
              <Stat icon={Sprout} label="Hectáreas" value={fmtNum(req.hectares)} />
            </dl>

            <div className="mt-5 pt-4 border-t border-border">
              <div className="text-xs uppercase tracking-wider font-semibold text-muted-foreground mb-2">Pesos de evaluación</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {(["precio", "plazo", "calidad", "condiciones"] as const).map((k) => (
                  <div key={k} className="flex items-center justify-between rounded-md bg-muted/60 px-2 py-1.5">
                    <span className="capitalize">{k}</span>
                    <span className="num font-bold text-primary">{req.weights[k]}%</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="card-soft p-5">
            <h2 className="text-sm font-bold mb-3">Items</h2>
            <ul className="divide-y divide-border">
              {req.items.map((it) => (
                <li key={it.id} className="py-2.5 first:pt-0 last:pb-0">
                  <div className="font-medium text-sm">{it.description}</div>
                  <div className="text-xs text-muted-foreground">{fmtNum(it.quantity)} {it.unit}{it.specs ? ` · ${it.specs}` : ""}</div>
                  {it.target_price && <div className="text-xs num text-foreground/70 mt-0.5">Target: {fmtPYG(it.target_price)} / {it.unit}</div>}
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* RIGHT */}
        <div className="xl:col-span-3">
          <section className="card-soft p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-bold">Cotizaciones recibidas</h2>
                <p className="text-xs text-muted-foreground">{validated} {validated === 1 ? "cotización validada" : "cotizaciones validadas"}</p>
              </div>
              <Link to="/cargar" className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90">
                <Upload className="h-4 w-4" /> Cargar cotización
              </Link>
            </div>

            <div className="overflow-x-auto -mx-2 px-2">
              <table className="w-full text-sm">
                <thead className="text-muted-foreground">
                  <tr className="text-left">
                    <th className="font-semibold py-2">Proveedor</th>
                    <th className="font-semibold py-2 text-right">Total normalizado</th>
                    <th className="font-semibold py-2 text-right">Plazo</th>
                    <th className="font-semibold py-2 text-right">Garantía</th>
                    <th className="font-semibold py-2">ML score</th>
                    <th className="font-semibold py-2 text-center">Anomalía</th>
                  </tr>
                </thead>
                <tbody>
                  {quotes.map((q) => (
                    <tr key={q.id} className="border-t border-border hover:bg-accent/40">
                      <td className="py-3">
                        <div className="font-semibold">{q.supplier_name}</div>
                        <div className="text-[11px] text-muted-foreground">{q.payment_terms}</div>
                      </td>
                      <td className="py-3 text-right num font-semibold">{fmtPYG(q.total_normalized_pyg)}</td>
                      <td className="py-3 text-right num">{q.delivery_days}d</td>
                      <td className="py-3 text-right num">{q.warranty_months}m</td>
                      <td className="py-3"><MLBand score={q.ml_score} /></td>
                      <td className="py-3 text-center relative">
                        {q.anomaly_flag ? (
                          <button
                            onMouseEnter={() => setHover(q.id)} onMouseLeave={() => setHover(null)}
                            onFocus={() => setHover(q.id)} onBlur={() => setHover(null)}
                            className="inline-flex items-center gap-1 text-warning-foreground"
                            aria-label={`Anomalía: ${q.anomaly_reason}`}
                          >
                            <AlertTriangle className="h-4 w-4 text-warning" />
                            <span className="text-[11px] font-semibold">Revisar</span>
                          </button>
                        ) : <span className="text-muted-foreground text-xs">—</span>}
                        {hover === q.id && q.anomaly_reason && (
                          <div className="absolute right-0 top-full mt-1 z-10 w-72 text-left text-xs bg-popover border border-border rounded-lg p-3 shadow-xl">
                            {q.anomaly_reason}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {quotes.length === 0 && (
                    <tr><td colSpan={6} className="py-10 text-center text-muted-foreground">Sin cotizaciones todavía. <Link to="/cargar" className="text-primary font-semibold hover:underline">Cargar la primera</Link>.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>

      {/* sticky action bar */}
      <div className="fixed bottom-0 left-0 right-0 md:left-64 z-20 border-t border-border bg-card/95 backdrop-blur px-6 py-3 flex items-center justify-end gap-2 shadow-lg">
        <Link
          to="/comparar/$id" params={{ id }}
          className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg border font-semibold ${validated >= 2 ? "border-border hover:bg-accent" : "opacity-50 pointer-events-none border-border"}`}
        >
          <GitCompareArrows className="h-4 w-4" /> Comparar cotizaciones
        </Link>
        <Link
          to="/comparar/$id" params={{ id }}
          className={`inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg font-semibold ${validated >= 2 ? "bg-primary text-primary-foreground hover:bg-primary/90" : "bg-muted text-muted-foreground pointer-events-none"}`}
        >
          <Sparkles className="h-4 w-4" /> Generar recomendación
        </Link>
      </div>
    </PageShell>
  );
}

function Stat({ icon: Icon, label, value, highlight }: { icon: typeof Sprout; label: string; value: string; highlight?: boolean }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold flex items-center gap-1">
        <Icon className="h-3 w-3" aria-hidden /> {label}
      </dt>
      <dd className={`mt-0.5 text-sm font-semibold ${highlight ? "text-destructive" : "text-foreground"}`}>{value}</dd>
    </div>
  );
}
