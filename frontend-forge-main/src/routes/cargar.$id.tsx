import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Pill } from "@/components/agro/Pill";
import {
  buildQuotationPayload,
  procurementApi,
  toUiSupplier,
  type ExtractedQuotation,
} from "@/lib/agro/api";
import { fmtPYG } from "@/lib/agro/format";
import type { Supplier } from "@/lib/agro/types";
import { CheckCircle2, FileText, Loader2, Sparkles, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

export const Route = createFileRoute("/cargar/$id")({
  head: () => ({
    meta: [
      { title: "Cargar cotización · AgroBuy" },
      { name: "description", content: "Procesar y guardar una cotización con IA." },
    ],
  }),
  component: CargarPage,
});

const SAMPLE = `Cotización N° 4421
Tecnomyl SA - RUC 80012345-6
Fecha: 2026-04-22

Producto: Urea granulada 46% N
Cantidad: 800 ton
Precio unitario: Gs. 4.650.000 / ton
Total: Gs. 3.720.000.000
Plazo de entrega: 12 días
Garantía: 6 meses
Condiciones: 30/60 días sin recargo
Stock confirmado en puerto de Villeta.`;

function CargarPage() {
  const { id } = Route.useParams();
  const [tab, setTab] = useState<"texto" | "archivo">("texto");
  const [text, setText] = useState(SAMPLE);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [supplier, setSupplier] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [step, setStep] = useState(0);
  const [extracted, setExtracted] = useState<ExtractedQuotation | null>(null);

  const messages = ["Analizando con IA…", "Detectando moneda y plazos…", "Validando datos…"];

  useEffect(() => {
    procurementApi
      .listSuppliers()
      .then((rows) => {
        const mapped = rows.map(toUiSupplier);
        setSuppliers(mapped);
        setSupplier((current) => current || mapped[0]?.id || "");
      })
      .catch((err: Error) => toast.error(err.message));
  }, []);

  async function process() {
    if (!text.trim()) {
      toast.error("Paste quotation text before processing");
      return;
    }
    setLoading(true);
    setStep(0);
    try {
      for (let i = 0; i < messages.length; i++) {
        await new Promise((r) => setTimeout(r, 250));
        setStep(i);
      }
      const result = await procurementApi.extractQuotation(id, text);
      setExtracted(result);
      toast.success("Quotation extracted");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not extract quotation");
    } finally {
      setLoading(false);
    }
  }

  async function saveQuotation() {
    if (!supplier) {
      toast.error("Register or select a supplier first");
      return;
    }
    if (!extracted) return;
    setSaving(true);
    try {
      await procurementApi.uploadQuotation(
        buildQuotationPayload({
          requestId: id,
          supplierId: supplier,
          rawText: text,
          extracted,
        }),
      );
      toast.success("Quotation saved and validated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not save quotation");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Cargar cotización</h2>
          <p className="text-sm text-muted-foreground mt-1">Solicitud {id}</p>
        </div>
        <Link
          to="/solicitud/$id"
          params={{ id }}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Volver al detalle
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-5">
        <Card className="p-5">
          <div className="flex gap-1 p-1 bg-secondary rounded-lg w-fit mb-4">
            {(["texto", "archivo"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={[
                  "px-3 py-1.5 rounded-md text-sm font-semibold transition-colors capitalize",
                  tab === t ? "bg-card text-foreground shadow-soft" : "text-muted-foreground",
                ].join(" ")}
                aria-pressed={tab === t}
              >
                {t === "texto" ? "Pegar texto" : "Subir archivo"}
              </button>
            ))}
          </div>

          {tab === "texto" ? (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={14}
              className="w-full rounded-lg bg-background border border-input px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-ring"
              aria-label="Texto de la cotización"
            />
          ) : (
            <label className="block border-2 border-dashed border-border rounded-xl p-10 text-center cursor-pointer hover:border-primary/50 hover:bg-secondary/40 transition-colors">
              <Upload className="size-8 text-muted-foreground mx-auto" aria-hidden />
              <div className="mt-3 font-semibold text-foreground">Arrastrar archivo</div>
              <div className="text-xs text-muted-foreground mt-1">PDF, Excel o imagen · MVP</div>
              <input type="file" className="sr-only" />
            </label>
          )}

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-3 items-end">
            <div>
              <label className="block text-[12px] font-semibold mb-1.5 text-foreground">
                Proveedor
              </label>
              <select
                value={supplier}
                onChange={(e) => setSupplier(e.target.value)}
                className="w-full rounded-lg bg-background border border-input px-3 py-2 text-sm"
              >
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.legal_name}
                  </option>
                ))}
              </select>
              {suppliers.length === 0 && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Register suppliers on the supplier page before saving quotations.
                </p>
              )}
            </div>
            <button
              onClick={process}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow disabled:opacity-60"
            >
              {loading ? (
                <Loader2 className="size-4 animate-spin" aria-hidden />
              ) : (
                <Sparkles className="size-4" aria-hidden />
              )}
              {loading ? messages[step] : "Procesar con IA"}
            </button>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-foreground flex items-center gap-2">
            <FileText className="size-4" aria-hidden /> Resultado de extracción
          </h3>
          {!extracted ? (
            <div className="mt-6 text-center text-sm text-muted-foreground py-8">
              Procese una cotización para ver la extracción estructurada.
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <Editable
                  label="Total"
                  value={`${extracted.currency} ${Number(extracted.total_amount).toLocaleString("es-PY")}`}
                  conf={Number(extracted.extraction_confidence)}
                />
                <Editable
                  label="Plazo (días)"
                  value={String(extracted.lead_time_days)}
                  conf={Number(extracted.extraction_confidence)}
                />
                <Editable
                  label="Garantía (meses)"
                  value={String(extracted.warranty_months ?? "-")}
                  conf={Number(extracted.extraction_confidence)}
                  low={Number(extracted.extraction_confidence) < 0.75}
                />
                <Editable
                  label="Condiciones de pago"
                  value={extracted.payment_terms ?? "-"}
                  conf={Number(extracted.extraction_confidence)}
                />
              </div>
              <div>
                <div className="text-[12px] font-semibold mb-1.5 text-foreground">Items</div>
                <div className="rounded-lg border border-border overflow-hidden">
                  {extracted.items.map((it, i) => (
                    <div key={i} className="px-3 py-2 text-sm flex items-center justify-between">
                      <div>
                        <div className="font-medium">{it.description}</div>
                        <div className="text-xs text-muted-foreground">
                          {Number(it.quantity).toLocaleString("es-PY")} unit ·{" "}
                          {fmtPYG(Number(it.unit_price))}/unit
                        </div>
                      </div>
                      <Pill tone="success">
                        conf {Math.round(Number(extracted.extraction_confidence) * 100)}%
                      </Pill>
                    </div>
                  ))}
                  {extracted.items.length === 0 && (
                    <div className="px-3 py-2 text-sm text-muted-foreground">
                      No line items detected. The quotation can still be saved with total and terms.
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={saveQuotation}
                disabled={saving}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow"
              >
                {saving ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                ) : (
                  <CheckCircle2 className="size-4" aria-hidden />
                )}
                Confirmar y guardar
              </button>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}

function Editable({
  label,
  value,
  conf,
  low,
}: {
  label: string;
  value: string;
  conf: number;
  low?: boolean;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </label>
        <span
          className={`text-[10px] font-semibold ${low ? "text-warning-foreground" : "text-success"}`}
        >
          {Math.round(conf * 100)}%
        </span>
      </div>
      <input
        defaultValue={value}
        className={[
          "w-full rounded-lg bg-background border px-3 py-2 text-sm",
          low ? "border-warning ring-1 ring-warning/30" : "border-input",
        ].join(" ")}
      />
    </div>
  );
}
