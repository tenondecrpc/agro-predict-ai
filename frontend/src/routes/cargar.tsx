import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { PageShell } from "@/components/PageShell";
import { api } from "@/lib/api";
import { fmtPYG } from "@/lib/format";
import { toast } from "sonner";
import { FileText, Upload, Sparkles, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { Quotation } from "@/lib/types";

export const Route = createFileRoute("/cargar")({
  component: CargarPage,
  head: () => ({ meta: [{ title: "Cargar cotización — AgroBuy" }] }),
});

const inputCls = "w-full rounded-lg bg-background border border-input px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

function CargarPage() {
  const navigate = useNavigate();
  const { data: suppliers = [] } = useQuery({ queryKey: ["suppliers"], queryFn: api.listSuppliers });
  const [tab, setTab] = useState<"texto" | "archivo">("texto");
  const [text, setText] = useState("");
  const [supplierId, setSupplierId] = useState("sup-tecnomyl");
  const [requestId, setRequestId] = useState("pr-001");
  const [extracted, setExtracted] = useState<Partial<Quotation> | null>(null);
  const [loadingMsg, setLoadingMsg] = useState("");

  const extract = useMutation({
    mutationFn: () => api.extractQuotation(text || "Cotización por 800 ton de urea — total Gs. 5.300.000.000 — entrega 16 días", requestId),
    onSuccess: (d) => {
      setExtracted(d);
      toast.success("Cotización extraída con IA");
    },
  });

  const save = useMutation({
    mutationFn: () => api.createQuotation({ ...extracted, request_id: requestId, supplier_id: supplierId, supplier_name: suppliers.find((s) => s.id === supplierId)?.legal_name } as any),
    onSuccess: () => {
      toast.success("Cotización guardada");
      navigate({ to: "/solicitud/$id", params: { id: requestId } });
    },
  });

  useEffect(() => {
    if (!extract.isPending) return;
    const msgs = ["Analizando con IA…", "Detectando moneda y plazos…", "Validando datos…"];
    let i = 0;
    setLoadingMsg(msgs[0]);
    const t = setInterval(() => { i = (i + 1) % msgs.length; setLoadingMsg(msgs[i]); }, 1000);
    return () => clearInterval(t);
  }, [extract.isPending]);

  return (
    <PageShell title="Cargar cotización" subtitle="Pegá texto o subí archivo · la IA extrae los datos">
      <div className="max-w-4xl mx-auto space-y-5">
        <div className="card-soft p-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
            <label className="block">
              <span className="text-xs font-semibold text-foreground/80">Solicitud asociada</span>
              <select className={`${inputCls} mt-1.5`} value={requestId} onChange={(e) => setRequestId(e.target.value)}>
                <option value="pr-001">pr-001 — Urea 800 ton</option>
                <option value="pr-002">pr-002 — Semilla soja BMX</option>
                <option value="pr-003">pr-003 — Glifosato 30.000 lt</option>
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold text-foreground/80">Proveedor</span>
              <select className={`${inputCls} mt-1.5`} value={supplierId} onChange={(e) => setSupplierId(e.target.value)}>
                {suppliers.map((s) => <option key={s.id} value={s.id}>{s.legal_name}</option>)}
                <option value="__new">+ Nuevo proveedor</option>
              </select>
            </label>
          </div>

          <div className="flex border-b border-border mb-3">
            {([["texto", "Pegar texto", FileText], ["archivo", "Subir archivo", Upload]] as const).map(([k, l, Icon]) => (
              <button
                key={k} onClick={() => setTab(k)}
                className={`px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px inline-flex items-center gap-2 ${tab === k ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"}`}
              >
                <Icon className="h-4 w-4" /> {l}
              </button>
            ))}
          </div>

          {tab === "texto" ? (
            <textarea
              rows={10} className={inputCls} value={text} onChange={(e) => setText(e.target.value)}
              placeholder="Pegá aquí el texto de la cotización (email, PDF copiado, etc.). La IA detecta moneda, plazo, garantía y precios."
            />
          ) : (
            <div className="border-2 border-dashed border-border rounded-xl px-6 py-12 text-center bg-muted/30">
              <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
              <p className="text-sm font-semibold">Arrastrá un PDF, Excel o imagen aquí</p>
              <p className="text-xs text-muted-foreground mt-1">MVP: subida real próximamente. Por ahora usá la pestaña de texto.</p>
            </div>
          )}

          <div className="mt-4 flex items-center justify-end gap-2">
            <button
              onClick={() => extract.mutate()}
              disabled={extract.isPending}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 disabled:opacity-70"
            >
              <Sparkles className="h-4 w-4" /> {extract.isPending ? loadingMsg : "Procesar con IA"}
            </button>
          </div>
        </div>

        {extracted && (
          <div className="card-soft p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" /> Datos extraídos · revisá y confirmá
              </h2>
              <span className="text-xs text-muted-foreground">Confianza IA: <b className="num text-foreground">{Math.round((extracted.confidence ?? 0.8) * 100)}%</b></span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ConfField label="Total (Gs.)" lowConf={(extracted.confidence ?? 1) < 0.8}>
                <input type="number" className={`${inputCls} num`} value={extracted.total_pyg ?? 0} onChange={(e) => setExtracted({ ...extracted, total_pyg: Number(e.target.value), total_normalized_pyg: Number(e.target.value) })} />
                <span className="text-[11px] text-muted-foreground">{fmtPYG(extracted.total_pyg ?? 0)}</span>
              </ConfField>
              <ConfField label="Plazo (días)">
                <input type="number" className={`${inputCls} num`} value={extracted.delivery_days ?? 0} onChange={(e) => setExtracted({ ...extracted, delivery_days: Number(e.target.value) })} />
              </ConfField>
              <ConfField label="Garantía (meses)">
                <input type="number" className={`${inputCls} num`} value={extracted.warranty_months ?? 0} onChange={(e) => setExtracted({ ...extracted, warranty_months: Number(e.target.value) })} />
              </ConfField>
              <ConfField label="Términos de pago">
                <input className={inputCls} value={extracted.payment_terms ?? ""} onChange={(e) => setExtracted({ ...extracted, payment_terms: e.target.value })} />
              </ConfField>
              <ConfField label="Moneda">
                <select className={inputCls} value={extracted.currency ?? "PYG"} onChange={(e) => setExtracted({ ...extracted, currency: e.target.value as "PYG" | "USD" })}>
                  <option value="PYG">PYG</option><option value="USD">USD</option>
                </select>
              </ConfField>
            </div>

            <div className="mt-5 flex items-center justify-end gap-2">
              <button onClick={() => setExtracted(null)} className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-accent">Descartar</button>
              <button onClick={() => save.mutate()} disabled={save.isPending} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90">
                <CheckCircle2 className="h-4 w-4" /> Confirmar y guardar
              </button>
            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
}

function ConfField({ label, children, lowConf }: { label: string; children: React.ReactNode; lowConf?: boolean }) {
  return (
    <label className={`block ${lowConf ? "" : ""}`}>
      <span className="text-xs font-semibold text-foreground/80 flex items-center gap-1">
        {label} {lowConf && <AlertTriangle className="h-3 w-3 text-warning" aria-label="Baja confianza" />}
      </span>
      <div className={`mt-1.5 ${lowConf ? "ring-2 ring-warning/40 rounded-lg" : ""}`}>{children}</div>
    </label>
  );
}
