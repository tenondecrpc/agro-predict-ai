import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { api } from "@/lib/api";
import { fmtPYG, fmtPct } from "@/lib/format";
import { MLBand } from "@/components/Pills";
import {
  AlertTriangle, CheckCircle2, Sparkles, Trophy, Clock, ShieldCheck,
  Mail, Copy, Edit3, Send, Sliders, Sprout, TrendingUp, CloudRain, Gauge,
} from "lucide-react";
import { toast } from "sonner";
import type { Quotation } from "@/lib/types";

export const Route = createFileRoute("/comparar/$id")({
  component: CompararPage,
  head: () => ({ meta: [{ title: "Comparar y recomendar — AgroBuy" }] }),
});

function CompararPage() {
  const { id } = Route.useParams();
  const { data: req } = useQuery({ queryKey: ["request", id], queryFn: () => api.getRequest(id) });
  const { data: quotes = [] } = useQuery({ queryKey: ["quotes", id], queryFn: () => api.listQuotations(id) });
  const recommend = useMutation({ mutationFn: () => api.recommend(id) });

  // auto-trigger first time
  useMemo(() => { if (quotes.length >= 2 && !recommend.data && !recommend.isPending) recommend.mutate(); }, [quotes.length]); // eslint-disable-line

  return (
    <PageShell title="Comparar y recomendar" subtitle={req?.title ?? id}>
      <div className="space-y-7 pb-10">
        {/* REGION 1: comparison table */}
        <ComparativaTable quotes={quotes} />

        {/* REGION 2: recommendation */}
        <RecomendacionCard rec={recommend.data} loading={recommend.isPending} onRetry={() => recommend.mutate()} />

        {/* REGION 3: negotiation */}
        <NegociacionCard quotes={quotes} defaultSupplierId={recommend.data?.recommended_supplier_id} />
      </div>
    </PageShell>
  );
}

function ComparativaTable({ quotes }: { quotes: Quotation[] }) {
  const bestPrice = quotes.length ? Math.min(...quotes.map((q) => q.total_normalized_pyg)) : 0;
  const fastest = quotes.length ? Math.min(...quotes.map((q) => q.delivery_days)) : 0;

  const winners = useMemo(() => {
    if (!quotes.length) return null;
    const best = (key: keyof Quotation, dir: "min" | "max") => {
      const v = quotes.map((q) => q[key] as number);
      const target = dir === "min" ? Math.min(...v) : Math.max(...v);
      return quotes.find((q) => (q[key] as number) === target)!;
    };
    return {
      precio: best("total_normalized_pyg", "min"),
      plazo: best("delivery_days", "min"),
      garantia: best("warranty_months", "max"),
      ml: best("ml_score", "max"),
    };
  }, [quotes]);

  return (
    <section className="card-soft overflow-hidden">
      <header className="px-5 py-4 border-b border-border bg-gradient-to-br from-primary-soft to-transparent">
        <h2 className="text-base font-bold flex items-center gap-2"><Trophy className="h-4 w-4 text-primary" /> Tabla comparativa normalizada</h2>
        <p className="text-xs text-muted-foreground mt-0.5">Todos los valores convertidos a Gs. y normalizados a la unidad solicitada.</p>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-muted-foreground bg-muted/40">
              <th className="font-semibold px-4 py-3 sticky left-0 bg-muted/40">Criterio</th>
              {quotes.map((q) => (
                <th key={q.id} className="font-semibold px-4 py-3 min-w-[200px]">
                  <div className="text-foreground">{q.supplier_name}</div>
                  <div className="mt-1"><MLBand score={q.ml_score} /></div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="num">
            <Row label="Total normalizado (Gs.)" cells={quotes.map((q) => ({
              value: fmtPYG(q.total_normalized_pyg),
              tone: q.total_normalized_pyg === bestPrice ? "good" : undefined,
              flag: q.anomaly_flag ? { icon: AlertTriangle, label: "Anomalía", reason: q.anomaly_reason } : undefined,
            }))} />
            <Row label="Plazo de entrega" cells={quotes.map((q) => ({
              value: `${q.delivery_days} días`,
              tone: q.delivery_days === fastest ? "info" : undefined,
            }))} />
            <Row label="Garantía" cells={quotes.map((q) => ({ value: `${q.warranty_months} meses` }))} />
            <Row label="Términos de pago" cells={quotes.map((q) => ({ value: q.payment_terms }))} />
            <Row label="ML p_on_time" cells={quotes.map((q) => ({ value: fmtPct(q.ml_p_on_time) }))} />
            <Row label="Anomaly score" cells={quotes.map((q) => ({
              value: q.anomaly_flag ? "Detectada" : "—",
              tone: q.anomaly_flag ? "warn" : undefined,
            }))} />
          </tbody>
          {winners && (
            <tfoot>
              <tr className="border-t-2 border-border bg-primary/5">
                <td className="px-4 py-3 font-bold text-primary text-xs uppercase tracking-wider">Mejor en cada criterio</td>
                <td colSpan={quotes.length} className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Chip icon={Trophy}>Mejor precio: {winners.precio.supplier_name}</Chip>
                    <Chip icon={Clock}>Más rápido: {winners.plazo.supplier_name}</Chip>
                    <Chip icon={ShieldCheck}>Mayor garantía: {winners.garantia.supplier_name}</Chip>
                    <Chip icon={Sparkles}>Mejor ML: {winners.ml.supplier_name}</Chip>
                  </div>
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </section>
  );
}

function Row({ label, cells }: { label: string; cells: Array<{ value: string; tone?: "good" | "info" | "warn"; flag?: { icon: typeof AlertTriangle; label: string; reason?: string } }> }) {
  return (
    <tr className="border-t border-border">
      <td className="px-4 py-3 font-semibold text-foreground/85 sticky left-0 bg-card">{label}</td>
      {cells.map((c, i) => {
        const tone = c.tone === "good"
          ? "bg-success/15 text-success-foreground ring-1 ring-success/30"
          : c.tone === "info"
            ? "bg-info/10 text-info ring-1 ring-info/30"
            : c.tone === "warn"
              ? "bg-warning/15 text-warning-foreground ring-1 ring-warning/30"
              : "";
        return (
          <td key={i} className="px-4 py-3">
            <span className={`inline-flex items-center gap-1.5 rounded-md px-2 py-1 ${tone}`}>
              {c.flag && <c.flag.icon className="h-3.5 w-3.5 text-warning" aria-label={c.flag.label} />}
              <span className="font-semibold">{c.value}</span>
            </span>
            {c.flag?.reason && <div className="text-[11px] text-muted-foreground mt-1 max-w-[220px]">{c.flag.reason}</div>}
          </td>
        );
      })}
    </tr>
  );
}

function Chip({ icon: Icon, children }: { icon: typeof Trophy; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-card ring-1 ring-border px-3 py-1 text-xs font-semibold">
      <Icon className="h-3.5 w-3.5 text-primary" aria-hidden /> {children}
    </span>
  );
}

function RecomendacionCard({ rec, loading, onRetry }: { rec: any; loading: boolean; onRetry: () => void }) {
  if (loading || !rec) {
    return (
      <section className="card-soft p-8 text-center">
        <Sparkles className="h-8 w-8 mx-auto text-primary animate-pulse" />
        <p className="mt-3 text-sm font-semibold">Generando recomendación con IA…</p>
        <p className="text-xs text-muted-foreground mt-1">Analizando precio, ML, clima y volatilidad.</p>
      </section>
    );
  }

  const bandLabel: Record<string, { label: string; cls: string }> = {
    alta_confianza: { label: "Alta confianza", cls: "bg-success/20 text-success-foreground ring-success/40" },
    media_confianza: { label: "Media confianza", cls: "bg-warning/20 text-warning-foreground ring-warning/40" },
    revisar: { label: "Revisar", cls: "bg-destructive/15 text-destructive ring-destructive/40" },
  };
  const band = bandLabel[rec.decision_band];

  return (
    <section className="card-soft overflow-hidden">
      <header className="px-6 py-5 border-b border-border bg-gradient-to-br from-primary/10 via-primary-soft/40 to-transparent">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wider font-bold text-primary mb-1.5 flex items-center gap-1.5">
              <Sparkles className="h-3.5 w-3.5" aria-hidden /> Recomendación generada
            </div>
            <h2 className="text-2xl font-bold tracking-tight">{rec.recommended_supplier_name}</h2>
            <div className="mt-2">
              <span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold ring-1 ${band.cls}`}>
                <CheckCircle2 className="h-3.5 w-3.5" /> {band.label}
              </span>
            </div>
          </div>

          <CircularScore score={rec.composite_score} />
        </div>
      </header>

      <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ScoreCard
          title="Urgency Score" total={rec.urgency_score.total}
          icon={CloudRain}
          bars={[
            { label: "Clima", value: rec.urgency_score.weather, icon: CloudRain },
            { label: "Plazo entrega", value: rec.urgency_score.delivery, icon: Clock },
            { label: "Volatilidad mercado", value: rec.urgency_score.volatility, icon: TrendingUp },
          ]}
        />
        <ScoreCard
          title="Offer Score" total={rec.offer_score.total}
          icon={Gauge}
          bars={[
            { label: "Histórico proveedor", value: rec.offer_score.supplier, icon: ShieldCheck },
            { label: "Términos comerciales", value: rec.offer_score.terms, icon: Sprout },
            { label: "Riesgo de entrega", value: rec.offer_score.delivery_risk, icon: Clock },
          ]}
        />
      </div>

      <div className="px-6 pb-6 grid grid-cols-1 lg:grid-cols-3 gap-5">
        <MdCard title="Justificación" md={rec.justification_md} />
        <MdCard title="Alternativas consideradas" md={rec.alternatives_md} />
        <MdCard title="Riesgos identificados" md={rec.risks_md} />
      </div>

      <div className="px-6 py-4 border-t border-border bg-muted/30 flex items-center justify-end gap-2">
        <button onClick={onRetry} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg border border-border hover:bg-accent font-semibold">
          <Sliders className="h-4 w-4" /> Ajustar criterios
        </button>
        <button onClick={() => toast.success("Recomendación aceptada · adjudicación pendiente de aprobador")} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90">
          <CheckCircle2 className="h-4 w-4" /> Aceptar recomendación
        </button>
      </div>
    </section>
  );
}

function CircularScore({ score }: { score: number }) {
  const r = 38, c = 2 * Math.PI * r;
  const offset = c * (1 - score / 100);
  const tone = score >= 80 ? "var(--color-primary)" : score >= 60 ? "var(--color-warning)" : "var(--color-destructive)";
  return (
    <div className="relative h-24 w-24">
      <svg viewBox="0 0 100 100" className="h-24 w-24 -rotate-90">
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--color-border)" strokeWidth="9" />
        <circle cx="50" cy="50" r={r} fill="none" stroke={tone} strokeWidth="9" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold num">{score}</span>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Score</span>
      </div>
    </div>
  );
}

function ScoreCard({ title, total, icon: Icon, bars }: { title: string; total: number; icon: typeof CloudRain; bars: Array<{ label: string; value: number; icon: typeof CloudRain }> }) {
  return (
    <div className="rounded-xl border border-border bg-gradient-to-br from-card to-muted/30 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold flex items-center gap-2"><Icon className="h-4 w-4 text-primary" aria-hidden /> {title}</h3>
        <span className="text-2xl font-bold num text-primary">{total}</span>
      </div>
      <div className="space-y-3">
        {bars.map((b) => (
          <div key={b.label}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="flex items-center gap-1.5 text-foreground/80"><b.icon className="h-3 w-3" aria-hidden /> {b.label}</span>
              <span className="num font-semibold">{b.value}</span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div className="h-full bg-gradient-to-r from-primary to-success rounded-full" style={{ width: `${b.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MdCard({ title, md }: { title: string; md: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h4 className="text-xs uppercase tracking-wider font-bold text-muted-foreground mb-2">{title}</h4>
      <div className="text-sm space-y-2">{renderMd(md)}</div>
    </div>
  );
}

function renderMd(md: string) {
  // tiny markdown: paragraphs, bullets, **bold**
  const blocks = md.split(/\n\n+/);
  return blocks.map((b, i) => {
    if (b.trim().startsWith("- ")) {
      const items = b.split("\n").filter((l) => l.trim().startsWith("- "));
      return (
        <ul key={i} className="list-disc pl-5 space-y-1.5 text-foreground/90">
          {items.map((it, j) => <li key={j}>{renderInline(it.replace(/^-\s*/, ""))}</li>)}
        </ul>
      );
    }
    return <p key={i} className="text-foreground/90 leading-relaxed">{renderInline(b)}</p>;
  });
}

function renderInline(s: string) {
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") ? <strong key={i} className="font-bold text-foreground">{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>,
  );
}

function NegociacionCard({ quotes, defaultSupplierId }: { quotes: Quotation[]; defaultSupplierId?: string }) {
  const [supplierId, setSupplierId] = useState(defaultSupplierId ?? quotes[0]?.supplier_id ?? "");
  const [tone, setTone] = useState<"cordial" | "formal" | "asertivo">("cordial");
  const [improvements, setImprovements] = useState({ precio: 5, plazo: 0, garantia: 0 });
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState("");
  const [subject, setSubject] = useState("");

  const negotiate = useMutation({
    mutationFn: () => api.negotiate(quotes.find((q) => q.supplier_id === supplierId)?.id ?? "", improvements, tone),
    onSuccess: (d) => { setBody(d.body); setSubject(d.subject); },
  });

  return (
    <section className="card-soft overflow-hidden">
      <header className="px-5 py-4 border-b border-border">
        <h2 className="text-base font-bold flex items-center gap-2"><Mail className="h-4 w-4 text-primary" /> Generador de mensaje de negociación</h2>
      </header>

      <div className="p-5 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <label className="block">
          <span className="text-xs font-semibold">Proveedor</span>
          <select className="mt-1.5 w-full rounded-lg bg-background border border-input px-3 py-2 text-sm" value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
            {quotes.map((q) => <option key={q.id} value={q.supplier_id}>{q.supplier_name}</option>)}
          </select>
        </label>

        <fieldset>
          <legend className="text-xs font-semibold mb-1.5">Mejoras buscadas</legend>
          <div className="space-y-1.5 text-sm">
            <ImprovInput label="Precio (% reducción)" value={improvements.precio} onChange={(v) => setImprovements({ ...improvements, precio: v })} />
            <ImprovInput label="Plazo (días menos)" value={improvements.plazo} onChange={(v) => setImprovements({ ...improvements, plazo: v })} />
            <ImprovInput label="Garantía (meses extra)" value={improvements.garantia} onChange={(v) => setImprovements({ ...improvements, garantia: v })} />
          </div>
        </fieldset>

        <fieldset>
          <legend className="text-xs font-semibold mb-1.5">Tono</legend>
          <div className="flex flex-col gap-1.5">
            {(["cordial", "formal", "asertivo"] as const).map((t) => (
              <label key={t} className="inline-flex items-center gap-2 text-sm cursor-pointer">
                <input type="radio" name="tone" checked={tone === t} onChange={() => setTone(t)} className="accent-[var(--color-primary)]" />
                <span className="capitalize">{t}</span>
              </label>
            ))}
          </div>
        </fieldset>
      </div>

      <div className="px-5 pb-4">
        <button
          onClick={() => negotiate.mutate()}
          disabled={negotiate.isPending}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:opacity-70"
        >
          <Sparkles className="h-4 w-4" /> {negotiate.isPending ? "Generando mensaje…" : "Generar mensaje"}
        </button>
      </div>

      {body && (
        <div className="px-5 pb-5">
          <div className="rounded-xl border border-border bg-gradient-to-br from-muted/40 to-card overflow-hidden">
            <div className="px-4 py-2.5 border-b border-border bg-card/60 flex items-center justify-between">
              <div className="text-xs"><b>Asunto:</b> {subject}</div>
              <div className="flex items-center gap-1">
                <button onClick={() => setEditing(!editing)} className="p-1.5 rounded hover:bg-accent" aria-label="Editar mensaje"><Edit3 className="h-3.5 w-3.5" /></button>
                <button onClick={() => { navigator.clipboard.writeText(body); toast.success("Copiado al portapapeles"); }} className="p-1.5 rounded hover:bg-accent" aria-label="Copiar"><Copy className="h-3.5 w-3.5" /></button>
              </div>
            </div>
            {editing ? (
              <textarea rows={14} className="w-full p-4 text-sm bg-transparent outline-none" value={body} onChange={(e) => setBody(e.target.value)} />
            ) : (
              <pre className="p-4 text-sm whitespace-pre-wrap font-sans text-foreground/90">{body}</pre>
            )}
            <div className="px-4 py-3 border-t border-border flex items-center justify-end gap-2">
              <button onClick={() => toast.success("Marcado como enviado")} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90">
                <Send className="h-3.5 w-3.5" /> Marcar como enviado
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ImprovInput({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <label className="flex items-center justify-between gap-2">
      <span className="text-xs">{label}</span>
      <input type="number" value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-20 num text-right rounded-md bg-background border border-input px-2 py-1 text-sm" />
    </label>
  );
}
