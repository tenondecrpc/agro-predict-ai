import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Kpi } from "@/components/agro/Kpi";
import { Pill } from "@/components/agro/Pill";
import { procurementApi, toUiRequest, toUiSupplier } from "@/lib/agro/api";
import { fmtPYG } from "@/lib/agro/format";
import type { PurchaseRequest, Supplier } from "@/lib/agro/types";
import { AlertTriangle, Briefcase, Clock, TrendingDown, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard ejecutivo · AgroBuy" },
      { name: "description", content: "KPIs y desempeño de compras." },
    ],
  }),
  component: DashboardPage,
});

const SPEND = [
  { m: "May", v: 1820 },
  { m: "Jun", v: 2140 },
  { m: "Jul", v: 1990 },
  { m: "Ago", v: 2780 },
  { m: "Sep", v: 3120 },
  { m: "Oct", v: 2890 },
  { m: "Nov", v: 3650 },
  { m: "Dic", v: 4080 },
  { m: "Ene", v: 3210 },
  { m: "Feb", v: 2980 },
  { m: "Mar", v: 3560 },
  { m: "Abr", v: 4210 },
];

const PIE = [
  { name: "Fertilizante", value: 42 },
  { name: "Fitosanitario", value: 22 },
  { name: "Semilla", value: 18 },
  { name: "Combustible", value: 12 },
  { name: "Repuesto", value: 6 },
];

const COLORS = [
  "oklch(0.52 0.14 152)",
  "oklch(0.66 0.17 150)",
  "oklch(0.55 0.13 70)",
  "oklch(0.78 0.16 75)",
  "oklch(0.6 0.13 235)",
];

function DashboardPage() {
  const [requests, setRequests] = useState<PurchaseRequest[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);

  useEffect(() => {
    Promise.all([procurementApi.listRequests(), procurementApi.listSuppliers()])
      .then(([requestRows, supplierRows]) => {
        setRequests(requestRows.map(toUiRequest));
        setSuppliers(supplierRows.map(toUiSupplier));
      })
      .catch(() => {
        setRequests([]);
        setSuppliers([]);
      });
  }, []);

  const activeSpend = useMemo(
    () =>
      requests
        .filter((r) => r.status !== "cerrada")
        .reduce((sum, r) => sum + r.total_estimated_pyg, 0),
    [requests],
  );
  const recommendedCount = requests.filter((r) => r.status === "recomendada").length;

  return (
    <AppShell>
      <div className="mb-5">
        <h2 className="text-xl font-bold tracking-tight text-foreground">Dashboard ejecutivo</h2>
        <p className="text-sm text-muted-foreground mt-1">Campaña 2026/27 · vista para director</p>
      </div>

      <Card className="p-4 mb-5 border-warning/40 bg-warning/8 flex items-center gap-3">
        <AlertTriangle className="size-5 text-warning shrink-0" aria-hidden />
        <div className="text-sm">
          <span className="font-semibold text-foreground">1 anomalía detectada este mes</span>
          <span className="text-muted-foreground">
            {" "}
            · Atlantic Comercio: precio 18% bajo mercado en cotización de urea.
          </span>
        </div>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Kpi
          label="Comprado este mes"
          value={fmtPYG(activeSpend)}
          sub={
            <span className="inline-flex items-center gap-1 text-success">
              <TrendingUp className="size-3" /> +18% vs mes anterior
            </span>
          }
          icon={<Briefcase className="size-5" />}
          tone="primary"
        />
        <Kpi
          label="Ahorro vs presupuesto"
          value="7.2%"
          sub={
            <span className="inline-flex items-center gap-1 text-success">
              <TrendingDown className="size-3" /> Gs. 318 M ahorrados
            </span>
          }
          icon={<TrendingDown className="size-5" />}
          tone="success"
        />
        <Kpi
          label="Cycle time promedio"
          value="8.4 días"
          sub="vs 11.2 trimestre anterior"
          icon={<Clock className="size-5" />}
          tone="info"
        />
        <Kpi
          label="Solicitudes adjudicadas"
          value={recommendedCount}
          sub="recomendadas"
          icon={<Briefcase className="size-5" />}
          tone="earth"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-5 mb-6">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-foreground">Gasto mensual (últimos 12 meses)</h3>
            <Pill tone="primary">Gs. millones</Pill>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={SPEND} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
                <defs>
                  <linearGradient id="g" x1="0" x2="1">
                    <stop offset="0%" stopColor="oklch(0.52 0.14 152)" />
                    <stop offset="100%" stopColor="oklch(0.66 0.17 150)" />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke="oklch(0.9 0.015 130)"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  dataKey="m"
                  tickLine={false}
                  axisLine={false}
                  stroke="oklch(0.48 0.02 140)"
                  fontSize={12}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  stroke="oklch(0.48 0.02 140)"
                  fontSize={12}
                />
                <Tooltip
                  contentStyle={{
                    background: "oklch(1 0 0)",
                    border: "1px solid oklch(0.9 0.015 130)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke="url(#g)"
                  strokeWidth={3}
                  dot={{ r: 3, fill: "oklch(0.52 0.14 152)" }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-5">
          <h3 className="font-semibold text-foreground mb-4">Gasto por categoría</h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={PIE}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={90}
                  paddingAngle={2}
                >
                  {PIE.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "oklch(1 0 0)",
                    border: "1px solid oklch(0.9 0.015 130)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                  formatter={(v) => `${v}%`}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            {PIE.map((p, i) => (
              <li key={p.name} className="flex items-center gap-1.5 text-muted-foreground">
                <span className="size-2 rounded-sm" style={{ background: COLORS[i] }} aria-hidden />
                {p.name}{" "}
                <span className="ml-auto tabular text-foreground font-semibold">{p.value}%</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Card className="overflow-hidden">
          <div className="px-5 py-4 border-b border-border font-semibold text-foreground">
            Top 5 proveedores adjudicados
          </div>
          <ul className="divide-y divide-border">
            {[...suppliers]
              .sort((a, b) => b.awards - a.awards)
              .slice(0, 5)
              .map((s, i) => (
                <li key={s.id} className="px-5 py-3 flex items-center gap-3">
                  <span className="size-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-foreground truncate">{s.legal_name}</div>
                    <div className="text-xs text-muted-foreground">
                      {s.primary_categories.join(" · ")}
                    </div>
                  </div>
                  <div className="tabular font-bold text-foreground">{s.awards}</div>
                </li>
              ))}
          </ul>
        </Card>

        <Card className="overflow-hidden">
          <div className="px-5 py-4 border-b border-border font-semibold text-foreground">
            Top 5 proveedores con mejor ML score
          </div>
          <ul className="divide-y divide-border">
            {[...suppliers]
              .sort((a, b) => b.ml_p_on_time - a.ml_p_on_time)
              .slice(0, 5)
              .map((s, i) => (
                <li key={s.id} className="px-5 py-3 flex items-center gap-3">
                  <span className="size-7 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-semibold text-foreground truncate">{s.legal_name}</div>
                    <div className="text-xs text-muted-foreground">RUC {s.ruc}</div>
                  </div>
                  <Pill
                    tone={
                      s.ml_p_on_time >= 0.8
                        ? "success"
                        : s.ml_p_on_time >= 0.6
                          ? "warning"
                          : "danger"
                    }
                  >
                    {Math.round(s.ml_p_on_time * 100)}
                  </Pill>
                </li>
              ))}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}
