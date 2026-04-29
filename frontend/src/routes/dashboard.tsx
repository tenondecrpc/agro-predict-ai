import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { PageShell } from "@/components/PageShell";
import { api } from "@/lib/api";
import { fmtPYG, fmtPct, fmtNum } from "@/lib/format";
import { TrendingUp, PiggyBank, Timer, Award, AlertTriangle } from "lucide-react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

export const Route = createFileRoute("/dashboard")({
  component: DashboardPage,
  head: () => ({ meta: [{ title: "Dashboard ejecutivo — AgroBuy" }] }),
});

const SPEND_12M = [
  { mes: "May", gasto: 1.2 }, { mes: "Jun", gasto: 1.8 }, { mes: "Jul", gasto: 2.1 },
  { mes: "Ago", gasto: 1.6 }, { mes: "Sep", gasto: 2.4 }, { mes: "Oct", gasto: 3.1 },
  { mes: "Nov", gasto: 4.2 }, { mes: "Dic", gasto: 3.6 }, { mes: "Ene", gasto: 2.9 },
  { mes: "Feb", gasto: 2.4 }, { mes: "Mar", gasto: 3.0 }, { mes: "Abr", gasto: 4.6 },
];

const BY_CATEGORY = [
  { name: "Fertilizante", value: 42, color: "var(--color-chart-1)" },
  { name: "Semilla", value: 22, color: "var(--color-chart-2)" },
  { name: "Fitosanitario", value: 18, color: "var(--color-chart-3)" },
  { name: "Combustible", value: 12, color: "var(--color-chart-4)" },
  { name: "Otros", value: 6, color: "var(--color-chart-5)" },
];

function DashboardPage() {
  const { data: quotes = [] } = useQuery({ queryKey: ["quotes", "pr-001"], queryFn: () => api.listQuotations("pr-001") });
  const anomalies = quotes.filter((q) => q.anomaly_flag).length;

  return (
    <PageShell title="Dashboard ejecutivo" subtitle="Visión consolidada · Cooperativa Yguazú · zafra 26/27">
      {anomalies > 0 && (
        <div className="mb-5 rounded-xl border border-warning/40 bg-warning/15 px-4 py-3 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-warning shrink-0" aria-hidden />
          <div className="text-sm">
            <span className="font-bold">Alerta de anomalías:</span> {anomalies} {anomalies === 1 ? "cotización flagged" : "cotizaciones flagged"} este mes. Revisar antes de adjudicar.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Hero icon={PiggyBank} label="Gs. comprado este mes" value={fmtPYG(4_600_000_000)} delta="+18% vs mes anterior" tone="primary" />
        <Hero icon={TrendingUp} label="Ahorro vs presupuesto" value="9,4%" delta="Gs. 480M ahorrados" tone="success" />
        <Hero icon={Timer} label="Cycle time promedio" value="11 días" delta="-3d vs trimestre" tone="info" />
        <Hero icon={Award} label="Solicitudes adjudicadas" value={fmtNum(28)} delta="+6 vs mes anterior" tone="earth" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mb-6">
        <section className="card-soft p-5 lg:col-span-2">
          <h2 className="text-sm font-bold mb-4">Gasto mensual · últimos 12 meses (Gs. miles de millones)</h2>
          <div className="h-72">
            <ResponsiveContainer>
              <LineChart data={SPEND_12M} margin={{ top: 5, right: 12, bottom: 0, left: -20 }}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="mes" stroke="var(--color-muted-foreground)" fontSize={12} />
                <YAxis stroke="var(--color-muted-foreground)" fontSize={12} />
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 12 }} formatter={(v: number) => [`Gs. ${v} mil M`, "Gasto"]} />
                <Line type="monotone" dataKey="gasto" stroke="var(--color-primary)" strokeWidth={3} dot={{ r: 3, fill: "var(--color-primary)" }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="card-soft p-5">
          <h2 className="text-sm font-bold mb-4">Gasto por categoría agro</h2>
          <div className="h-72">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={BY_CATEGORY} dataKey="value" nameKey="name" innerRadius={50} outerRadius={88} paddingAngle={2}>
                  {BY_CATEGORY.map((c) => <Cell key={c.name} fill={c.color} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "var(--color-popover)", border: "1px solid var(--color-border)", borderRadius: 10, fontSize: 12 }} formatter={(v: number) => `${v}%`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <TopTable
          title="Top 5 proveedores adjudicados"
          headers={["Proveedor", "Adjudic.", "Volumen"]}
          rows={[
            ["Tecnomyl SA", "21", fmtPYG(8_400_000_000)],
            ["Agrofertil SA", "14", fmtPYG(5_100_000_000)],
            ["Glymax Paraguay", "11", fmtPYG(3_200_000_000)],
            ["Ciabay SA", "7", fmtPYG(1_800_000_000)],
            ["Atlantic", "6", fmtPYG(1_200_000_000)],
          ]}
        />
        <TopTable
          title="Top 5 proveedores con mejor ML score"
          headers={["Proveedor", "ML p_on_time", "On-time hist."]}
          rows={[
            ["Tecnomyl SA", fmtPct(0.92), fmtPct(0.94)],
            ["Agrofertil SA", fmtPct(0.85), fmtPct(0.88)],
            ["Glymax Paraguay", fmtPct(0.81), fmtPct(0.83)],
            ["Ciabay SA", fmtPct(0.78), fmtPct(0.80)],
            ["Atlantic", fmtPct(0.71), fmtPct(0.74)],
          ]}
        />
      </div>
    </PageShell>
  );
}

function Hero({ icon: Icon, label, value, delta, tone }: { icon: typeof TrendingUp; label: string; value: string; delta: string; tone: "primary" | "success" | "info" | "earth" }) {
  const map = {
    primary: "from-primary/15 to-transparent text-primary",
    success: "from-success/15 to-transparent text-success-foreground",
    info: "from-info/10 to-transparent text-info",
    earth: "from-earth/15 to-transparent text-earth",
  };
  return (
    <div className={`card-soft p-5 bg-gradient-to-br ${map[tone]}`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider font-bold text-muted-foreground">{label}</div>
          <div className="mt-2 text-2xl kpi-num text-foreground">{value}</div>
          <div className="mt-1 text-xs text-muted-foreground">{delta}</div>
        </div>
        <Icon className="h-6 w-6 opacity-70" aria-hidden />
      </div>
    </div>
  );
}

function TopTable({ title, headers, rows }: { title: string; headers: string[]; rows: string[][] }) {
  return (
    <section className="card-soft overflow-hidden">
      <header className="px-5 py-4 border-b border-border"><h2 className="text-sm font-bold">{title}</h2></header>
      <table className="w-full text-sm">
        <thead className="text-muted-foreground bg-muted/40">
          <tr>{headers.map((h, i) => <th key={h} className={`font-semibold px-4 py-2.5 ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-border">
              {r.map((c, j) => <td key={j} className={`px-4 py-2.5 ${j === 0 ? "text-left font-semibold" : "text-right num"}`}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
