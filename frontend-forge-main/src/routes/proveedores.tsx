import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Pill } from "@/components/agro/Pill";
import { TENANT_ID, procurementApi, toUiSupplier } from "@/lib/agro/api";
import { fmtPct } from "@/lib/agro/format";
import type { Supplier } from "@/lib/agro/types";
import { Building2, CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

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
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [legalName, setLegalName] = useState("");
  const [ruc, setRuc] = useState("");
  const [category, setCategory] = useState("fertilizante");

  async function load() {
    setLoading(true);
    try {
      const rows = await procurementApi.listSuppliers();
      setSuppliers(rows.map(toUiSupplier));
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not load suppliers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createSupplier() {
    if (!legalName.trim()) {
      toast.error("Supplier name is required");
      return;
    }
    try {
      await procurementApi.createSupplier({
        tenant_id: TENANT_ID,
        legal_name: legalName,
        ruc: ruc || null,
        primary_categories: category,
        country: "PY",
        risk_tier: "unknown",
      });
      setLegalName("");
      setRuc("");
      toast.success("Supplier created");
      await load();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not create supplier");
    }
  }

  return (
    <AppShell>
      <div className="mb-5">
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Catálogo de proveedores
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          {suppliers.length} proveedores activos · ordenados por confianza ML
        </p>
      </div>

      <Card className="p-5 mb-5">
        <div className="grid grid-cols-1 md:grid-cols-[1.2fr_160px_180px_auto] gap-3 items-end">
          <div>
            <label className="block text-[12px] font-semibold mb-1.5 text-foreground">
              Proveedor
            </label>
            <input
              className="w-full rounded-lg bg-background border border-input px-3 py-2 text-sm"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
              placeholder="Legal name"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold mb-1.5 text-foreground">RUC</label>
            <input
              className="w-full rounded-lg bg-background border border-input px-3 py-2 text-sm"
              value={ruc}
              onChange={(e) => setRuc(e.target.value)}
              placeholder="80000000-0"
            />
          </div>
          <div>
            <label className="block text-[12px] font-semibold mb-1.5 text-foreground">
              Categoría
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg bg-background border border-input px-3 py-2 text-sm"
            >
              <option value="fertilizante">Fertilizante</option>
              <option value="semilla">Semilla</option>
              <option value="fitosanitario">Fitosanitario</option>
              <option value="maquinaria">Maquinaria</option>
              <option value="repuesto">Repuesto</option>
              <option value="combustible">Combustible</option>
            </select>
          </div>
          <button
            type="button"
            onClick={createSupplier}
            className="rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow"
          >
            Registrar
          </button>
        </div>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading && <Card className="p-5 text-sm text-muted-foreground">Loading suppliers...</Card>}
        {!loading && suppliers.length === 0 && (
          <Card className="p-5 text-sm text-muted-foreground">
            Register suppliers before uploading quotations.
          </Card>
        )}
        {[...suppliers]
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
                  <Pill key={c} tone="earth">
                    {c}
                  </Pill>
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
      <div className="text-[10px] uppercase tracking-wider font-semibold text-muted-foreground">
        {label}
      </div>
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
        <circle
          cx="25"
          cy="25"
          r={r}
          stroke="currentColor"
          strokeOpacity="0.2"
          strokeWidth="5"
          fill="none"
        />
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
