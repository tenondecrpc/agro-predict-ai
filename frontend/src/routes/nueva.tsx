import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { api } from "@/lib/api";
import { fmtPYG } from "@/lib/format";
import { toast } from "sonner";
import { Trash2, Plus, Save, Send, Sprout } from "lucide-react";
import type { PRItem } from "@/lib/types";

export const Route = createFileRoute("/nueva")({
  component: NuevaPage,
  head: () => ({ meta: [{ title: "Nueva solicitud — AgroBuy" }] }),
});

const inputCls =
  "w-full rounded-lg bg-background border border-input px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring placeholder:text-muted-foreground";

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="card-soft p-5">
      <header className="mb-4">
        <h2 className="text-base font-bold text-foreground">{title}</h2>
        {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
      </header>
      {children}
    </section>
  );
}

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-foreground/80">{label}</span>
      <div className="mt-1.5">{children}</div>
      {hint && <span className="text-[11px] text-muted-foreground mt-1 block">{hint}</span>}
    </label>
  );
}

function NuevaPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "", description: "", category: "fertilizante",
    target_crop: "soja", zafra: "2026/27", fenological_window: "Pre-siembra",
    hectares: 1000, department: "Itapúa",
    deadline: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
    budget_pyg: 0, urgency: "media",
  });
  const [weights, setWeights] = useState({ precio: 40, plazo: 30, calidad: 20, condiciones: 10 });
  const [items, setItems] = useState<PRItem[]>([
    { id: "1", description: "", quantity: 1, unit: "ton", specs: "", target_price: 0 },
  ]);

  const totalWeights = useMemo(
    () => weights.precio + weights.plazo + weights.calidad + weights.condiciones,
    [weights],
  );
  const valid = totalWeights === 100;

  const create = useMutation({
    mutationFn: (publish: boolean) => api.createRequest({ ...form, weights, items, status: publish ? "publicada" : "borrador" } as any),
    onSuccess: (_d, publish) => {
      toast.success(publish ? "Solicitud publicada" : "Borrador guardado");
      navigate({ to: "/" });
    },
    onError: () => toast.error("No se pudo guardar la solicitud"),
  });

  return (
    <PageShell title="Nueva solicitud de compra" subtitle="Cooperativa Yguazú · creando solicitud nueva">
      <div className="max-w-5xl mx-auto space-y-5 pb-32">
        <Section title="Datos generales">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Field label="Título de la solicitud">
              <input className={inputCls} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Ej. Compra de 800 ton de urea para zafra soja 26/27" />
            </Field>
            <Field label="Categoría">
              <select className={inputCls} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {["fertilizante", "semilla", "fitosanitario", "maquinaria", "repuesto", "combustible"].map((c) => (
                  <option key={c} value={c} className="capitalize">{c}</option>
                ))}
              </select>
            </Field>
            <Field label="Descripción" hint="Contexto que ayude a los proveedores a cotizar">
              <textarea rows={3} className={inputCls} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </Field>
            <div />
          </div>
        </Section>

        <Section title="Contexto agro" subtitle="Datos productivos asociados a la solicitud">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Cultivo destino">
              <select className={inputCls} value={form.target_crop} onChange={(e) => setForm({ ...form, target_crop: e.target.value })}>
                {["soja", "maiz", "trigo", "sorgo", "girasol", "arroz"].map((c) => <option key={c} value={c} className="capitalize">{c}</option>)}
              </select>
            </Field>
            <Field label="Zafra">
              <input className={inputCls} value={form.zafra} onChange={(e) => setForm({ ...form, zafra: e.target.value })} />
            </Field>
            <Field label="Ventana fenológica">
              <input className={inputCls} value={form.fenological_window} onChange={(e) => setForm({ ...form, fenological_window: e.target.value })} placeholder="Ej. Pre-siembra · V2-V4" />
            </Field>
            <Field label="Hectáreas a cubrir">
              <input type="number" className={`${inputCls} num`} value={form.hectares} onChange={(e) => setForm({ ...form, hectares: Number(e.target.value) })} />
            </Field>
            <Field label="Departamento de entrega">
              <select className={inputCls} value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>
                {["Itapúa", "Alto Paraná", "Canindeyú", "Caaguazú", "San Pedro", "Misiones"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </Field>
          </div>
        </Section>

        <Section title="Plazo y presupuesto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Field label="Fecha límite">
              <input type="date" className={inputCls} value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
            </Field>
            <Field label="Presupuesto estimado (Gs.)">
              <input type="number" className={`${inputCls} num`} value={form.budget_pyg} onChange={(e) => setForm({ ...form, budget_pyg: Number(e.target.value) })} />
              {form.budget_pyg > 0 && <span className="text-[11px] text-muted-foreground mt-1 block">{fmtPYG(form.budget_pyg)}</span>}
            </Field>
            <Field label="Urgencia">
              <div className="flex gap-2 flex-wrap">
                {(["baja", "media", "alta", "critica"] as const).map((u) => (
                  <label key={u} className={`px-3 py-1.5 rounded-full text-xs font-semibold cursor-pointer ring-1 ${form.urgency === u ? "bg-primary text-primary-foreground ring-primary" : "bg-card ring-border hover:bg-accent"}`}>
                    <input type="radio" name="urg" className="sr-only" checked={form.urgency === u} onChange={() => setForm({ ...form, urgency: u })} />
                    <span className="capitalize">{u}</span>
                  </label>
                ))}
              </div>
            </Field>
          </div>
        </Section>

        <Section title="Pesos de evaluación" subtitle="Indica qué importa más al evaluar las cotizaciones. Total debe ser 100.">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
            {(["precio", "plazo", "calidad", "condiciones"] as const).map((k) => (
              <div key={k}>
                <div className="flex items-center justify-between text-sm mb-1.5">
                  <span className="font-semibold capitalize">{k}</span>
                  <span className="num text-primary font-bold">{weights[k]}</span>
                </div>
                <input
                  type="range" min={0} max={100} value={weights[k]}
                  onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })}
                  className="w-full accent-[var(--color-primary)]"
                  aria-label={`Peso ${k}`}
                />
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-end gap-2">
            <span className="text-xs text-muted-foreground">Total:</span>
            <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-bold num ring-1 ${valid ? "bg-success/20 text-success-foreground ring-success/40" : "bg-destructive/15 text-destructive ring-destructive/40"}`}>
              {totalWeights} / 100
            </span>
          </div>
        </Section>

        <Section title="Items a cotizar">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-muted-foreground">
                <tr className="text-left">
                  <th className="font-semibold py-2 pr-2">Descripción</th>
                  <th className="font-semibold py-2 pr-2 w-24">Cantidad</th>
                  <th className="font-semibold py-2 pr-2 w-24">Unidad</th>
                  <th className="font-semibold py-2 pr-2">Especificaciones</th>
                  <th className="font-semibold py-2 pr-2 w-36">Precio target (Gs.)</th>
                  <th className="w-10" />
                </tr>
              </thead>
              <tbody>
                {items.map((it, i) => (
                  <tr key={it.id} className="border-t border-border">
                    <td className="py-2 pr-2"><input className={inputCls} value={it.description} onChange={(e) => { const x = [...items]; x[i] = { ...it, description: e.target.value }; setItems(x); }} /></td>
                    <td className="py-2 pr-2"><input type="number" className={`${inputCls} num`} value={it.quantity} onChange={(e) => { const x = [...items]; x[i] = { ...it, quantity: Number(e.target.value) }; setItems(x); }} /></td>
                    <td className="py-2 pr-2"><input className={inputCls} value={it.unit} onChange={(e) => { const x = [...items]; x[i] = { ...it, unit: e.target.value }; setItems(x); }} /></td>
                    <td className="py-2 pr-2"><input className={inputCls} value={it.specs ?? ""} onChange={(e) => { const x = [...items]; x[i] = { ...it, specs: e.target.value }; setItems(x); }} /></td>
                    <td className="py-2 pr-2"><input type="number" className={`${inputCls} num`} value={it.target_price ?? 0} onChange={(e) => { const x = [...items]; x[i] = { ...it, target_price: Number(e.target.value) }; setItems(x); }} /></td>
                    <td className="py-2">
                      <button onClick={() => setItems(items.filter((x) => x.id !== it.id))} className="p-1.5 text-muted-foreground hover:text-destructive" aria-label="Eliminar item">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            onClick={() => setItems([...items, { id: `${Date.now()}`, description: "", quantity: 1, unit: "ton", specs: "", target_price: 0 }])}
            className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-primary hover:underline"
          >
            <Plus className="h-4 w-4" /> Agregar item
          </button>
        </Section>
      </div>

      {/* Sticky action bar */}
      <div className="fixed bottom-0 left-0 right-0 md:left-64 z-20 border-t border-border bg-card/95 backdrop-blur px-6 py-3 flex items-center justify-between shadow-lg">
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <Sprout className="h-4 w-4 text-primary" aria-hidden />
          {valid ? "Listo para publicar." : "Ajustá los pesos para sumar 100 antes de publicar."}
        </div>
        <div className="flex gap-2">
          <Link to="/" className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-accent">Cancelar</Link>
          <button onClick={() => create.mutate(false)} className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg border border-border hover:bg-accent font-semibold">
            <Save className="h-4 w-4" /> Guardar borrador
          </button>
          <button
            onClick={() => create.mutate(true)}
            disabled={!valid || !form.title}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground font-semibold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" /> Publicar solicitud
          </button>
        </div>
      </div>
    </PageShell>
  );
}
