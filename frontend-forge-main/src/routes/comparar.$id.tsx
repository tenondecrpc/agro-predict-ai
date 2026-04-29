import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Pill } from "@/components/agro/Pill";
import { MlBand } from "@/components/agro/agro-pills";
import { QUOTATIONS, RECOMMENDATION, REQUESTS, SUPPLIERS } from "@/lib/agro/mock";
import { fmtPYG, fmtPct } from "@/lib/agro/format";
import {
  AlertTriangle,
  CheckCircle2,
  Cloud,
  Copy,
  Edit3,
  Loader2,
  Send,
  Sparkles,
  TrendingUp,
  Truck,
  Wind,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

export const Route = createFileRoute("/comparar/$id")({
  head: () => ({
    meta: [
      { title: "Comparar y recomendar · AgroBuy" },
      { name: "description", content: "Tabla comparativa, recomendación IA y generador de mensaje." },
    ],
  }),
  component: CompararPage,
});

function CompararPage() {
  const { id } = Route.useParams();
  const req = REQUESTS.find((r) => r.id === id)!;
  const quotes = QUOTATIONS.filter((q) => q.request_id === id);
  const rec = RECOMMENDATION;
  const recommendedSup = SUPPLIERS.find((s) => s.id === rec.recommended_supplier_id)!;

  const best = useMemo(() => {
    const minTotal = Math.min(...quotes.map((q) => q.total_pyg));
    const minDelivery = Math.min(...quotes.map((q) => q.delivery_days));
    return { minTotal, minDelivery };
  }, [quotes]);

  return (
    <AppShell>
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
          <Sparkles className="size-3.5 text-primary-glow" aria-hidden />
          <span className="uppercase tracking-wider font-semibold">Comparar y recomendar</span>
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">{req.title}</h2>
      </div>

      {/* Region 1 — comparative table */}
      <Card className="overflow-hidden mb-6">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-semibold text-foreground">Tabla comparativa normalizada</h3>
          <Pill tone="primary">{quotes.length} cotizaciones · PYG normalizado</Pill>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-secondary/40">
                <th className="text-left px-5 py-3 text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
                  Criterio
                </th>
                {quotes.map((q) => {
                  const sup = SUPPLIERS.find((s) => s.id === q.supplier_id)!;
                  const isRec = q.supplier_id === rec.recommended_supplier_id;
                  return (
                    <th key={q.id} className={[
                      "text-left px-4 py-3 align-top min-w-[180px]",
                      isRec ? "bg-primary/8" : "",
                    ].join(" ")}>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-foreground">{sup.legal_name}</span>
                        {isRec && <Pill tone="primary">Recomendado</Pill>}
                      </div>
                      <div className="mt-1.5"><MlBand score={q.ml_score} /></div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              <Row label="Items unificados">
                {quotes.map((q) => (
                  <td key={q.id} className="px-4 py-3 text-foreground">
                    Urea 46% · 800 ton
                  </td>
                ))}
              </Row>
              <Row label="Total normalizado (Gs.)">
                {quotes.map((q) => (
                  <td
                    key={q.id}
                    className={[
                      "px-4 py-3 font-bold tabular text-foreground",
                      q.total_pyg === best.minTotal ? "bg-success/12 text-success" : "",
                    ].join(" ")}
                  >
                    {fmtPYG(q.total_pyg)}
                    {q.total_pyg === best.minTotal && (
                      <span className="ml-2 text-[10px] font-semibold uppercase">Mejor precio</span>
                    )}
                  </td>
                ))}
              </Row>
              <Row label="Plazo de entrega">
                {quotes.map((q) => (
                  <td
                    key={q.id}
                    className={[
                      "px-4 py-3 tabular",
                      q.delivery_days === best.minDelivery ? "bg-info/12 text-info font-semibold" : "text-foreground",
                    ].join(" ")}
                  >
                    {q.delivery_days} días
                    {q.delivery_days === best.minDelivery && (
                      <span className="ml-2 text-[10px] font-semibold uppercase">Más rápido</span>
                    )}
                  </td>
                ))}
              </Row>
              <Row label="Garantía">
                {quotes.map((q) => (
                  <td key={q.id} className="px-4 py-3 tabular text-foreground">{q.warranty_months} meses</td>
                ))}
              </Row>
              <Row label="Condiciones de pago">
                {quotes.map((q) => (
                  <td key={q.id} className="px-4 py-3 text-foreground">{q.payment_terms}</td>
                ))}
              </Row>
              <Row label="ML p_on_time">
                {quotes.map((q) => (
                  <td key={q.id} className="px-4 py-3 tabular text-foreground">{fmtPct(q.ml_p_on_time, 0)}</td>
                ))}
              </Row>
              <Row label="Anomalía">
                {quotes.map((q) => (
                  <td key={q.id} className="px-4 py-3">
                    {q.anomaly ? (
                      <span className="inline-flex items-center gap-1.5 text-warning-foreground" title={q.anomaly_reason}>
                        <AlertTriangle className="size-4 text-warning" aria-hidden />
                        <span className="text-xs font-semibold">Detectada</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-success">
                        <CheckCircle2 className="size-4" aria-hidden />
                        <span className="text-xs font-semibold">Limpia</span>
                      </span>
                    )}
                  </td>
                ))}
              </Row>
            </tbody>
            <tfoot>
              <tr className="bg-secondary/30 border-t border-border">
                <td className="px-5 py-3 text-[11px] uppercase tracking-wider font-semibold text-muted-foreground">
                  Mejor en cada criterio
                </td>
                <td colSpan={quotes.length} className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <Pill tone="success">Precio: Atlantic (anómalo)</Pill>
                    <Pill tone="info">Plazo: Tecnomyl</Pill>
                    <Pill tone="primary">Confianza ML: Tecnomyl</Pill>
                    <Pill tone="earth">Condiciones: Agrofertil</Pill>
                  </div>
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </Card>

      {/* Region 2 — Recommendation */}
      <Card className="overflow-hidden mb-6 border-primary/30">
        <div className="bg-hero-gradient text-primary-foreground px-6 py-5">
          <div className="flex items-start gap-4 flex-wrap">
            <div className="flex-1 min-w-0">
              <div className="text-[11px] uppercase tracking-widest font-semibold opacity-90 flex items-center gap-2">
                <Sparkles className="size-3.5" aria-hidden /> Recomendación generada
              </div>
              <h3 className="mt-1 text-2xl font-bold tracking-tight">
                {recommendedSup.legal_name}
              </h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 backdrop-blur px-3 py-1 text-xs font-semibold">
                  <CheckCircle2 className="size-3.5" aria-hidden />
                  Alta confianza
                </span>
                <span className="text-xs opacity-90">
                  RUC {recommendedSup.ruc} · entrega 12 días
                </span>
              </div>
            </div>
            <CompositeScore value={rec.composite_score} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 p-5 border-b border-border">
          <ScoreCard
            title="Urgency Score"
            total={rec.urgency_score.total}
            tone="earth"
            rows={[
              { label: "Clima (lluvia ventana V4-V6)", value: rec.urgency_score.weather, icon: <Cloud className="size-3.5" aria-hidden /> },
              { label: "Riesgo logístico", value: rec.urgency_score.delivery, icon: <Truck className="size-3.5" aria-hidden /> },
              { label: "Volatilidad PYG/USD", value: rec.urgency_score.volatility, icon: <TrendingUp className="size-3.5" aria-hidden /> },
            ]}
          />
          <ScoreCard
            title="Offer Score"
            total={rec.offer_score.total}
            tone="primary"
            rows={[
              { label: "Confianza proveedor", value: rec.offer_score.supplier, icon: <CheckCircle2 className="size-3.5" aria-hidden /> },
              { label: "Términos y condiciones", value: rec.offer_score.terms, icon: <Wind className="size-3.5" aria-hidden /> },
              { label: "Riesgo de entrega", value: rec.offer_score.delivery_risk, icon: <Truck className="size-3.5" aria-hidden /> },
            ]}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 p-5">
          <Markdown title="Justificación" body={rec.justification_md} />
          <Markdown title="Alternativas consideradas" body={rec.alternatives_md} />
          <Markdown title="Riesgos identificados" body={rec.risks_md} />
        </div>

        <div className="px-5 py-4 border-t border-border flex items-center justify-end gap-3 bg-secondary/30">
          <button
            onClick={() => toast.message("Ajuste de pesos abierto")}
            className="rounded-lg bg-secondary px-4 py-2 text-sm font-semibold text-secondary-foreground hover:bg-secondary/70"
          >
            Ajustar criterios
          </button>
          <button
            onClick={() => toast.success("Recomendación aceptada — pasando a aprobación")}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow"
          >
            <CheckCircle2 className="size-4" aria-hidden /> Aceptar recomendación
          </button>
        </div>
      </Card>

      {/* Region 3 — Negotiation message generator */}
      <NegotiationGenerator defaultSupplier={rec.recommended_supplier_id} />
    </AppShell>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr className="border-t border-border">
      <td className="px-5 py-3 font-semibold text-foreground bg-secondary/20 align-top">{label}</td>
      {children}
    </tr>
  );
}

function CompositeScore({ value }: { value: number }) {
  const r = 38;
  const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  return (
    <div className="relative size-24 shrink-0" role="img" aria-label={`Composite score ${value} de 100`}>
      <svg viewBox="0 0 100 100" className="size-24 -rotate-90">
        <circle cx="50" cy="50" r={r} stroke="currentColor" strokeOpacity="0.25" strokeWidth="8" fill="none" />
        <circle
          cx="50"
          cy="50"
          r={r}
          stroke="white"
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-2xl font-bold tabular leading-none">{value}</div>
        <div className="text-[10px] uppercase tracking-wider opacity-90 mt-1">composite</div>
      </div>
    </div>
  );
}

function ScoreCard({
  title,
  total,
  tone,
  rows,
}: {
  title: string;
  total: number;
  tone: "primary" | "earth";
  rows: { label: string; value: number; icon: React.ReactNode }[];
}) {
  const barTone = tone === "primary" ? "bg-primary-gradient" : "bg-earth";
  return (
    <div className="rounded-xl border border-border p-4 bg-card">
      <div className="flex items-center justify-between mb-3">
        <div className="font-semibold text-foreground">{title}</div>
        <div className="text-2xl font-bold tabular text-foreground">{total}</div>
      </div>
      <div className="space-y-2.5">
        {rows.map((r) => (
          <div key={r.label}>
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                {r.icon} {r.label}
              </span>
              <span className="tabular font-semibold text-foreground">{r.value}</span>
            </div>
            <div className="h-2 rounded-full bg-secondary overflow-hidden">
              <div className={`h-full ${barTone}`} style={{ width: `${r.value}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Markdown({ title, body }: { title: string; body: string }) {
  // Tiny markdown renderer for our 3 fields (bold + lists)
  const lines = body.split("\n");
  return (
    <div>
      <div className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">
        {title}
      </div>
      <div className="text-sm text-foreground space-y-2">
        {lines.map((ln, i) => {
          if (ln.startsWith("- ")) {
            return (
              <div key={i} className="flex gap-2">
                <span className="text-primary mt-1.5 size-1.5 rounded-full bg-primary shrink-0" aria-hidden />
                <span dangerouslySetInnerHTML={{ __html: inline(ln.slice(2)) }} />
              </div>
            );
          }
          if (!ln.trim()) return null;
          return <p key={i} dangerouslySetInnerHTML={{ __html: inline(ln) }} />;
        })}
      </div>
    </div>
  );
}

function inline(s: string) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-primary font-semibold">$1</strong>');
}

function NegotiationGenerator({ defaultSupplier }: { defaultSupplier: string }) {
  const [supplier, setSupplier] = useState(defaultSupplier);
  const [improve, setImprove] = useState({ precio: true, plazo: true, garantia: false });
  const [tone, setTone] = useState<"cordial" | "formal" | "asertivo">("cordial");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  async function generate() {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 1700));
    const sup = SUPPLIERS.find((s) => s.id === supplier)!;
    const greeting =
      tone === "cordial" ? "Estimados," : tone === "formal" ? "Señores:" : "Equipo,";
    const ask: string[] = [];
    if (improve.precio) ask.push("- Una **mejora del 3–5% en el precio unitario**, considerando el volumen comprometido (800 ton).");
    if (improve.plazo) ask.push("- Reducir el plazo de entrega a **10 días o menos**, para anticipar la ventana fenológica V4–V6.");
    if (improve.garantia) ask.push("- Ampliar la **garantía a 9 meses**, alineada al ciclo de almacenamiento previsto.");

    setMsg(
      `${greeting}

Junto con saludarles, agradecemos su cotización N° 4421 por urea 46% para la zafra 2026/27 de la Cooperativa Yguazú.

Hemos analizado las propuestas recibidas y ${sup.legal_name} se ubica en el primer lugar de nuestra evaluación, con una probabilidad de entrega a tiempo del 92% y stock confirmado en Villeta. Para cerrar la operación quisiéramos solicitar:

${ask.join("\n")}

Quedamos atentos a su revisión hasta el viernes próximo. Cualquier ajuste que puedan facilitar nos permitirá adjudicar de forma inmediata.

Saludos cordiales,
Ana Rojas — Compras
Cooperativa Yguazú · Itapúa, Paraguay`,
    );
    setEditing(false);
    setLoading(false);
  }

  return (
    <Card className="overflow-hidden">
      <div className="px-5 py-4 border-b border-border">
        <h3 className="font-semibold text-foreground flex items-center gap-2">
          <Send className="size-4" aria-hidden /> Generador de mensaje de negociación
        </h3>
      </div>

      <div className="p-5 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4 items-end border-b border-border">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-[12px] font-semibold mb-1.5 text-foreground">Proveedor</label>
            <select
              value={supplier}
              onChange={(e) => setSupplier(e.target.value)}
              className="w-full rounded-lg bg-background border border-input px-3 py-2 text-sm"
            >
              {SUPPLIERS.map((s) => (
                <option key={s.id} value={s.id}>{s.legal_name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[12px] font-semibold mb-1.5 text-foreground">Mejorar</label>
            <div className="flex flex-wrap gap-2">
              {([
                ["precio", "precio %"],
                ["plazo", "plazo días"],
                ["garantia", "garantía meses"],
              ] as const).map(([k, l]) => (
                <label key={k} className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs font-semibold cursor-pointer hover:border-primary/40">
                  <input
                    type="checkbox"
                    checked={improve[k]}
                    onChange={(e) => setImprove({ ...improve, [k]: e.target.checked })}
                    className="accent-[oklch(0.52_0.14_152)]"
                  />
                  {l}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-[12px] font-semibold mb-1.5 text-foreground">Tono</label>
            <div className="flex gap-1 p-1 bg-secondary rounded-lg w-fit">
              {(["cordial", "formal", "asertivo"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTone(t)}
                  className={[
                    "px-3 py-1 rounded-md text-xs font-semibold capitalize",
                    tone === t ? "bg-card text-foreground shadow-soft" : "text-muted-foreground",
                  ].join(" ")}
                  aria-pressed={tone === t}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow disabled:opacity-60"
        >
          {loading ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Sparkles className="size-4" aria-hidden />}
          {loading ? "Generando…" : "Generar mensaje"}
        </button>
      </div>

      {msg && (
        <div className="p-5">
          <div className="rounded-xl border border-border overflow-hidden">
            <div className="bg-secondary/40 px-4 py-2 text-xs font-semibold text-muted-foreground flex items-center justify-between">
              <span>Para: {SUPPLIERS.find((s) => s.id === supplier)?.legal_name}</span>
              <span>Asunto: Cotización urea 46% · Cooperativa Yguazú</span>
            </div>
            {editing ? (
              <textarea
                className="w-full p-4 text-sm font-mono bg-card focus:outline-none min-h-[280px]"
                value={msg}
                onChange={(e) => setMsg(e.target.value)}
              />
            ) : (
              <pre className="whitespace-pre-wrap p-4 text-sm font-sans text-foreground leading-relaxed">
                {msg}
              </pre>
            )}
          </div>
          <div className="mt-3 flex flex-wrap gap-2 justify-end">
            <button
              onClick={() => setEditing((v) => !v)}
              className="inline-flex items-center gap-2 rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-secondary-foreground hover:bg-secondary/70"
            >
              <Edit3 className="size-4" aria-hidden /> {editing ? "Vista" : "Editar"}
            </button>
            <button
              onClick={() => {
                navigator.clipboard?.writeText(msg);
                toast.success("Mensaje copiado al portapapeles");
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-secondary-foreground hover:bg-secondary/70"
            >
              <Copy className="size-4" aria-hidden /> Copiar
            </button>
            <button
              onClick={() => toast.success("Marcado como enviado")}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient px-3 py-1.5 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow"
            >
              <Send className="size-4" aria-hidden /> Marcar como enviado
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}
