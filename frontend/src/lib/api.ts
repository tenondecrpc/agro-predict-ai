import { REQUESTS, QUOTATIONS, SUPPLIERS, RECOMMENDATION } from "./mockData";
import type { PurchaseRequest, Quotation, Supplier, Recommendation, NegotiationMessage } from "./types";

const API_BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";
export const TENANT_ID = "tenant-yguazu";
export const TEAM_ID = "team-compras";
export const CURRENT_USER = { name: "Ana Rojas", email: "comprador@yguazu.coop.py", role: "Comprador" };

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

async function tryFetch<T>(path: string, init?: RequestInit, fallback?: () => T | Promise<T>): Promise<T> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: ctrl.signal,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    clearTimeout(t);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()) as T;
  } catch {
    if (fallback) return fallback();
    throw new Error("API offline");
  }
}

export const api = {
  listRequests: () =>
    tryFetch<PurchaseRequest[]>(
      `/api/v1/procurement/requests?tenant_id=${TENANT_ID}&team_id=${TEAM_ID}`,
      undefined,
      () => REQUESTS,
    ),

  getRequest: async (id: string) => {
    const all = await api.listRequests();
    return all.find((r) => r.id === id);
  },

  createRequest: (body: Partial<PurchaseRequest>) =>
    tryFetch<PurchaseRequest>(
      `/api/v1/procurement/requests`,
      { method: "POST", body: JSON.stringify({ ...body, tenant_id: TENANT_ID, team_id: TEAM_ID }) },
      async () => {
        await sleep(400);
        return { ...(body as PurchaseRequest), id: `pr-${Date.now()}`, status: "publicada", created_at: new Date().toISOString() };
      },
    ),

  listQuotations: (requestId: string) =>
    tryFetch<Quotation[]>(
      `/api/v1/procurement/requests/${requestId}/quotations?tenant_id=${TENANT_ID}`,
      undefined,
      () => QUOTATIONS.filter((q) => q.request_id === requestId),
    ),

  createQuotation: (body: Partial<Quotation>) =>
    tryFetch<Quotation>(
      `/api/v1/procurement/quotations`,
      { method: "POST", body: JSON.stringify({ ...body, tenant_id: TENANT_ID }) },
      async () => {
        await sleep(500);
        return { ...(body as Quotation), id: `q-${Date.now()}`, created_at: new Date().toISOString() };
      },
    ),

  extractQuotation: (raw_text: string, request_id: string) =>
    tryFetch<Partial<Quotation>>(
      `/api/v1/procurement/quotations/extract`,
      { method: "POST", body: JSON.stringify({ raw_text, request_id, tenant_id: TENANT_ID }) },
      async () => {
        await sleep(2800);
        // Heuristic mock extraction
        const totalMatch = raw_text.match(/(?:total|monto)[^\d]*([\d.,]+)/i);
        const total = totalMatch ? Number(totalMatch[1].replace(/\./g, "").replace(",", ".")) : 5_300_000_000;
        const daysMatch = raw_text.match(/(\d{1,3})\s*d[ií]as/i);
        return {
          supplier_name: "Proveedor detectado",
          total_pyg: total,
          total_normalized_pyg: total,
          currency: "PYG",
          delivery_days: daysMatch ? Number(daysMatch[1]) : 18,
          warranty_months: 12,
          payment_terms: "30/60 días",
          confidence: 0.78,
          items: [{ description: "Item extraído (revisar)", quantity: 1, unit_price_pyg: total, total }],
        };
      },
    ),

  recommend: (requestId: string) =>
    tryFetch<Recommendation>(
      `/api/v1/procurement/requests/${requestId}/recommend`,
      { method: "POST", body: JSON.stringify({ tenant_id: TENANT_ID }) },
      async () => {
        await sleep(1200);
        return RECOMMENDATION;
      },
    ),

  negotiate: (quotationId: string, target_improvements: Record<string, unknown>, tone: string) =>
    tryFetch<NegotiationMessage>(
      `/api/v1/procurement/quotations/${quotationId}/negotiate`,
      { method: "POST", body: JSON.stringify({ target_improvements, tone, tenant_id: TENANT_ID }) },
      async () => {
        await sleep(1800);
        const toneOpening: Record<string, string> = {
          cordial: "Estimados, espero se encuentren muy bien.",
          formal: "Estimados Sres.,",
          asertivo: "Estimados,",
        };
        const improvements: string[] = [];
        if (target_improvements.precio) improvements.push(`una mejora de precio del ${target_improvements.precio}%`);
        if (target_improvements.plazo) improvements.push(`reducir el plazo de entrega en ${target_improvements.plazo} días`);
        if (target_improvements.garantia) improvements.push(`extender la garantía a ${target_improvements.garantia} meses`);
        return {
          supplier_id: "sup-tecnomyl",
          subject: "Solicitud de revisión de cotización — Urea zafra 26/27",
          body: `${toneOpening[tone] || toneOpening.cordial}

Hemos recibido y analizado su cotización para la compra de 800 ton de urea destinada a la campaña soja 2026/27 de Cooperativa Yguazú. Apreciamos sinceramente su interés y la calidad de la propuesta presentada.

Considerando el volumen de la operación y la relación comercial sostenida con su empresa, quisiéramos solicitarles ${improvements.join(", ")}. Esta revisión nos permitiría avanzar con la adjudicación dentro de los plazos de la ventana fenológica V2-V4.

Quedamos atentos a su respuesta antes del cierre de evaluación.

Cordialmente,
Ana Rojas — Cooperativa Yguazú
comprador@yguazu.coop.py`,
        };
      },
    ),

  weatherRisk: (department = "Itapua", horizon_days = 10) =>
    tryFetch<{ risk: number; description: string }>(
      `/api/v1/procurement/weather/risk?department=${department}&horizon_days=${horizon_days}`,
      undefined,
      () => ({ risk: 0.42, description: "Lluvias moderadas pronosticadas días 8-12 en Itapúa." }),
    ),

  fxUsdPyg: () =>
    tryFetch<{ rate: number; ts: string }>(
      `/api/v1/procurement/fx/usd_pyg`,
      undefined,
      () => ({ rate: 7350, ts: new Date().toISOString() }),
    ),

  listSuppliers: () =>
    tryFetch<Supplier[]>(
      `/api/v1/procurement/suppliers?tenant_id=${TENANT_ID}`,
      undefined,
      () => SUPPLIERS,
    ),
};
