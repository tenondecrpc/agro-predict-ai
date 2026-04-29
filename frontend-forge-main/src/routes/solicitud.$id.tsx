import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Pill } from "@/components/agro/Pill";
import {
  CropIcon,
  MlBand,
  StatusPill,
  UrgencyPill,
  WeatherBadge,
} from "@/components/agro/agro-pills";
import { procurementApi, toUiQuotation, toUiRequest, toUiSupplier } from "@/lib/agro/api";
import { daysUntil, fmtDate, fmtPYG } from "@/lib/agro/format";
import type { PurchaseRequest, Quotation, Supplier } from "@/lib/agro/types";
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  MapPin,
  Package,
  Sparkles,
  Upload,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

export const Route = createFileRoute("/solicitud/$id")({
  head: ({ params }) => ({
    meta: [
      { title: `Solicitud ${params.id} · AgroBuy` },
      { name: "description", content: "Detalle de la solicitud y cotizaciones recibidas." },
    ],
  }),
  component: DetallePage,
  notFoundComponent: () => (
    <AppShell>
      <Card className="p-8 text-center">Solicitud no encontrada.</Card>
    </AppShell>
  ),
});

function DetallePage() {
  const { id } = Route.useParams();
  const router = useRouter();
  const [req, setReq] = useState<PurchaseRequest | null>(null);
  const [quotes, setQuotes] = useState<Quotation[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const validated = quotes.filter((q) => q.status === "validada").length;
  const [compared, setCompared] = useState(false);
  const suppliersById = useMemo(
    () => new Map(suppliers.map((supplier) => [supplier.id, supplier])),
    [suppliers],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      procurementApi.getRequest(id),
      procurementApi.listQuotations(id),
      procurementApi.listSuppliers(),
    ])
      .then(([request, quotations, supplierRows]) => {
        if (!active) return;
        setReq(toUiRequest(request));
        setQuotes(quotations.map(toUiQuotation));
        setSuppliers(supplierRows.map(toUiSupplier));
        setError(null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [id]);

  async function markReady() {
    if (validated < 2) return;
    try {
      await procurementApi.transitionRequest(id, "ready_for_review");
      setCompared(true);
      toast.success("Quotations normalized and ready for recommendation");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not compare quotations");
    }
  }

  if (loading)
    return (
      <AppShell>
        <Card className="p-8 text-center">Loading request...</Card>
      </AppShell>
    );
  if (error)
    return (
      <AppShell>
        <Card className="p-8 text-center text-destructive">{error}</Card>
      </AppShell>
    );
  if (!req)
    return (
      <AppShell>
        <Card className="p-8 text-center">Solicitud no encontrada.</Card>
      </AppShell>
    );

  return (
    <AppShell>
      <div className="flex items-start gap-3 mb-5">
        <button
          onClick={() => router.history.back()}
          className="text-sm text-muted-foreground hover:text-foreground"
        >
          ← Volver
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-5">
        {/* Left */}
        <div className="space-y-5">
          <Card className="p-5">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <StatusPill value={req.status} />
              <UrgencyPill value={req.urgency} />
              <Pill tone="earth">{req.fenological_window}</Pill>
              <CropIcon value={req.crop} />
            </div>
            <h2 className="text-xl font-bold tracking-tight text-foreground">{req.title}</h2>
            <p className="mt-2 text-sm text-muted-foreground">{req.description}</p>
            <div className="grid grid-cols-2 gap-3 mt-4 text-sm">
              <Info
                icon={<Calendar className="size-4" aria-hidden />}
                label="Fecha límite"
                value={`${fmtDate(req.deadline)} · ${daysUntil(req.deadline)} días`}
              />
              <Info
                icon={<MapPin className="size-4" aria-hidden />}
                label="Departamento"
                value={req.department}
              />
              <Info
                icon={<Package className="size-4" aria-hidden />}
                label="Hectáreas"
                value={req.hectares.toLocaleString("es-PY")}
              />
              <Info
                icon={<Sparkles className="size-4" aria-hidden />}
                label="Presupuesto"
                value={fmtPYG(req.budget_pyg)}
              />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <WeatherBadge />
              <Pill tone="neutral">PYG/USD: 7.380</Pill>
            </div>
          </Card>

          <Card className="p-5">
            <h3 className="font-semibold mb-3 text-foreground">Items solicitados</h3>
            <ul className="divide-y divide-border">
              {req.items.map((it) => (
                <li key={it.id} className="py-3">
                  <div className="font-medium text-foreground">{it.description}</div>
                  <div className="text-xs text-muted-foreground mt-1">{it.spec}</div>
                  <div className="mt-2 flex items-center gap-3 text-sm">
                    <span className="tabular font-semibold">
                      {it.qty.toLocaleString("es-PY")} {it.unit}
                    </span>
                    <span className="text-muted-foreground">·</span>
                    <span className="text-muted-foreground">
                      target {fmtPYG(it.target_price_pyg)}/{it.unit}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-5">
            <h3 className="font-semibold mb-3 text-foreground">Pesos de evaluación</h3>
            <div className="space-y-2">
              {Object.entries(req.weights).map(([k, v]) => (
                <div key={k}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="capitalize text-muted-foreground">{k}</span>
                    <span className="font-semibold text-foreground tabular">{v}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                    <div className="h-full bg-primary-gradient" style={{ width: `${v}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right */}
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-foreground">
              Cotizaciones{" "}
              <span className="text-muted-foreground font-normal">({quotes.length})</span>
            </h3>
            <Link
              to="/cargar/$id"
              params={{ id: req.id }}
              className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient text-primary-foreground px-3.5 py-2 text-sm font-semibold shadow-soft hover:shadow-glow"
            >
              <Upload className="size-4" aria-hidden /> Cargar cotización
            </Link>
          </div>

          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-[11px] uppercase tracking-wider text-muted-foreground bg-secondary/40">
                  <tr className="[&>th]:px-4 [&>th]:py-3 text-left">
                    <th>Proveedor</th>
                    <th className="text-right">Total (Gs.)</th>
                    <th>Plazo</th>
                    <th>Garantía</th>
                    <th>ML score</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {quotes.map((q) => {
                    const sup = suppliersById.get(q.supplier_id);
                    return (
                      <tr key={q.id} className="border-t border-border hover:bg-secondary/30">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-foreground flex items-center gap-2">
                            {sup?.legal_name ?? q.supplier_id}
                            {q.anomaly && (
                              <span
                                className="inline-flex items-center gap-1 text-warning-foreground"
                                title={q.anomaly_reason}
                              >
                                <AlertTriangle className="size-4 text-warning" aria-hidden />
                                <span className="sr-only">Anomalía: {q.anomaly_reason}</span>
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            RUC {sup?.ruc ?? "N/A"}
                          </div>
                        </td>
                        <td className="px-4 py-3 text-right font-semibold tabular">
                          {fmtPYG(q.total_pyg)}
                        </td>
                        <td className="px-4 py-3 tabular">{q.delivery_days} días</td>
                        <td className="px-4 py-3 tabular">{q.warranty_months} m</td>
                        <td className="px-4 py-3">
                          <MlBand score={q.ml_score} />
                        </td>
                        <td className="px-4 py-3 text-right">
                          <ArrowRight className="size-4 text-muted-foreground inline" aria-hidden />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {quotes.some((q) => q.anomaly) && (
            <Card className="p-4 border-warning/40 bg-warning/8">
              <div className="flex gap-3">
                <AlertTriangle className="size-5 text-warning shrink-0 mt-0.5" aria-hidden />
                <div className="text-sm">
                  <div className="font-semibold text-foreground">Anomalía detectada</div>
                  <p className="text-muted-foreground mt-1">
                    {quotes.find((q) => q.anomaly)?.anomaly_reason}
                  </p>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Sticky action bar */}
      <div className="sticky bottom-0 mt-6 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-3 bg-background/90 backdrop-blur border-t border-border flex items-center justify-end gap-3">
        <span className="text-xs text-muted-foreground mr-auto">
          {validated} cotizaciones validadas
        </span>
        <button
          type="button"
          disabled={validated < 2}
          onClick={markReady}
          className="inline-flex items-center gap-2 rounded-lg bg-secondary px-4 py-2 text-sm font-semibold text-secondary-foreground hover:bg-secondary/70 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Comparar cotizaciones
        </button>
        <Link
          to="/comparar/$id"
          params={{ id: req.id }}
          aria-disabled={!compared && validated < 2}
          className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow"
        >
          <Sparkles className="size-4" aria-hidden /> Generar recomendación
        </Link>
      </div>
    </AppShell>
  );
}

function Info({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-muted-foreground mt-0.5">{icon}</span>
      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
          {label}
        </div>
        <div className="text-foreground font-medium mt-0.5">{value}</div>
      </div>
    </div>
  );
}
