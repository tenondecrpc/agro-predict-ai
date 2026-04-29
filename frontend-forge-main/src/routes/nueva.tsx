import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/agro/AppShell";
import { Card } from "@/components/agro/Card";
import { Pill } from "@/components/agro/Pill";
import { fmtPYG } from "@/lib/agro/format";
import type { Weights } from "@/lib/agro/types";
import { useState } from "react";
import { Plus, Save, Send, Trash2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/nueva")({
  head: () => ({
    meta: [
      { title: "Nueva solicitud · AgroBuy" },
      { name: "description", content: "Crear una nueva solicitud de compra." },
    ],
  }),
  component: NuevaPage,
});

interface ItemRow {
  id: string;
  description: string;
  qty: number;
  unit: string;
  spec: string;
  target: number;
}

function NuevaPage() {
  const [weights, setWeights] = useState<Weights>({
    precio: 40,
    plazo: 25,
    calidad: 25,
    condiciones: 10,
  });
  const total = weights.precio + weights.plazo + weights.calidad + weights.condiciones;
  const ok = total === 100;

  const [items, setItems] = useState<ItemRow[]>([
    { id: "i1", description: "", qty: 0, unit: "ton", spec: "", target: 0 },
  ]);

  const subtotal = items.reduce((s, i) => s + i.qty * i.target, 0);

  return (
    <AppShell>
      <div className="mb-5">
        <h2 className="text-xl font-bold tracking-tight text-foreground">Nueva solicitud</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Defina el contexto agronómico, plazos y los pesos de evaluación que usará la IA.
        </p>
      </div>

      <div className="space-y-5">
        <Section title="Datos generales">
          <Field label="Título">
            <input className={inputCls} placeholder="Ej.: Compra de urea 46% para zafra 26/27" />
          </Field>
          <Field label="Descripción" full>
            <textarea rows={2} className={inputCls} placeholder="Contexto y motivación…" />
          </Field>
          <Field label="Categoría">
            <select className={inputCls}>
              <option>Fertilizante</option>
              <option>Semilla</option>
              <option>Fitosanitario</option>
              <option>Maquinaria</option>
              <option>Repuesto</option>
              <option>Combustible</option>
            </select>
          </Field>
        </Section>

        <Section title="Contexto agronómico">
          <Field label="Cultivo destino">
            <select className={inputCls}>
              <option>Soja</option>
              <option>Maíz</option>
              <option>Trigo</option>
              <option>Sorgo</option>
            </select>
          </Field>
          <Field label="Zafra">
            <input className={inputCls} defaultValue="2026/27" />
          </Field>
          <Field label="Ventana fenológica">
            <input className={inputCls} placeholder="Ej.: V4 — V6" />
          </Field>
          <Field label="Hectáreas a cubrir">
            <input type="number" className={inputCls} placeholder="0" />
          </Field>
          <Field label="Departamento de entrega">
            <select className={inputCls}>
              <option>Itapúa</option>
              <option>Alto Paraná</option>
              <option>Caaguazú</option>
              <option>Canindeyú</option>
              <option>San Pedro</option>
            </select>
          </Field>
        </Section>

        <Section title="Plazo y presupuesto">
          <Field label="Fecha límite">
            <input type="date" className={inputCls} />
          </Field>
          <Field label="Presupuesto estimado (Gs.)">
            <input type="number" className={inputCls} placeholder="0" />
          </Field>
          <Field label="Urgencia" full>
            <div className="flex flex-wrap gap-2">
              {(["baja", "media", "alta", "critica"] as const).map((u) => (
                <label key={u} className="cursor-pointer">
                  <input type="radio" name="urgency" className="peer sr-only" />
                  <span className="inline-flex items-center rounded-full border border-border bg-card px-3 py-1.5 text-sm font-medium peer-checked:bg-primary peer-checked:text-primary-foreground peer-checked:border-primary capitalize">
                    {u === "critica" ? "Crítica" : u}
                  </span>
                </label>
              ))}
            </div>
          </Field>
        </Section>

        <Section
          title="Pesos de evaluación"
          right={
            <Pill tone={ok ? "success" : "danger"}>
              Total: {total} {ok ? "✓" : "≠ 100"}
            </Pill>
          }
        >
          {(["precio", "plazo", "calidad", "condiciones"] as const).map((k) => (
            <div key={k} className="md:col-span-2">
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-sm font-medium capitalize text-foreground">{k}</label>
                <span className="text-sm tabular font-semibold text-primary">{weights[k]}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={weights[k]}
                onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })}
                className="w-full accent-[oklch(0.52_0.14_152)]"
                aria-label={`Peso ${k}`}
              />
            </div>
          ))}
        </Section>

        <Section
          title="Items"
          right={
            <button
              type="button"
              onClick={() =>
                setItems((it) => [
                  ...it,
                  {
                    id: `i${it.length + 1}`,
                    description: "",
                    qty: 0,
                    unit: "ton",
                    spec: "",
                    target: 0,
                  },
                ])
              }
              className="inline-flex items-center gap-1.5 rounded-lg bg-secondary px-3 py-1.5 text-sm font-semibold text-secondary-foreground hover:bg-secondary/70"
            >
              <Plus className="size-4" aria-hidden /> Agregar item
            </button>
          }
        >
          <div className="md:col-span-6 -mx-5 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-[11px] uppercase tracking-wider text-muted-foreground">
                <tr className="[&>th]:px-3 [&>th]:py-2 text-left">
                  <th>Descripción</th>
                  <th className="w-24">Cantidad</th>
                  <th className="w-24">Unidad</th>
                  <th>Especificaciones</th>
                  <th className="w-36">Precio target</th>
                  <th className="w-10"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it, idx) => (
                  <tr key={it.id} className="border-t border-border">
                    <td className="px-3 py-2">
                      <input
                        className={inputCls}
                        value={it.description}
                        onChange={(e) =>
                          setItems((arr) =>
                            arr.map((x, i) => (i === idx ? { ...x, description: e.target.value } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        className={inputCls}
                        value={it.qty || ""}
                        onChange={(e) =>
                          setItems((arr) =>
                            arr.map((x, i) => (i === idx ? { ...x, qty: Number(e.target.value) } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className={inputCls}
                        value={it.unit}
                        onChange={(e) =>
                          setItems((arr) =>
                            arr.map((x, i) => (i === idx ? { ...x, unit: e.target.value } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className={inputCls}
                        value={it.spec}
                        onChange={(e) =>
                          setItems((arr) =>
                            arr.map((x, i) => (i === idx ? { ...x, spec: e.target.value } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        className={inputCls}
                        value={it.target || ""}
                        onChange={(e) =>
                          setItems((arr) =>
                            arr.map((x, i) => (i === idx ? { ...x, target: Number(e.target.value) } : x)),
                          )
                        }
                      />
                    </td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => setItems((arr) => arr.filter((_, i) => i !== idx))}
                        className="text-muted-foreground hover:text-destructive"
                        aria-label="Eliminar item"
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t border-border">
                  <td colSpan={4} className="px-3 py-3 text-right text-sm font-semibold text-muted-foreground">
                    Subtotal estimado
                  </td>
                  <td className="px-3 py-3 font-bold tabular text-foreground">{fmtPYG(subtotal)}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </Section>

        <div className="sticky bottom-0 -mx-4 sm:-mx-6 lg:-mx-8 px-4 sm:px-6 lg:px-8 py-3 bg-background/90 backdrop-blur border-t border-border flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={() => toast.success("Borrador guardado")}
            className="inline-flex items-center gap-2 rounded-lg bg-secondary px-4 py-2 text-sm font-semibold text-secondary-foreground hover:bg-secondary/70"
          >
            <Save className="size-4" aria-hidden /> Guardar borrador
          </button>
          <Link
            to="/"
            onClick={() => toast.success("Solicitud publicada — los proveedores serán notificados")}
            className="inline-flex items-center gap-2 rounded-lg bg-primary-gradient px-4 py-2 text-sm font-semibold text-primary-foreground shadow-soft hover:shadow-glow"
          >
            <Send className="size-4" aria-hidden /> Publicar solicitud
          </Link>
        </div>
      </div>
    </AppShell>
  );
}

const inputCls =
  "w-full rounded-lg bg-background border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";

function Section({
  title,
  right,
  children,
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-foreground">{title}</h3>
        {right}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4">{children}</div>
    </Card>
  );
}

function Field({
  label,
  children,
  full = false,
}: {
  label: string;
  children: React.ReactNode;
  full?: boolean;
}) {
  return (
    <div className={full ? "md:col-span-6" : "md:col-span-2"}>
      <label className="block text-[12px] font-semibold text-foreground mb-1.5">{label}</label>
      {children}
    </div>
  );
}
