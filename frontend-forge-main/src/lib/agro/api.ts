import type {
  Category,
  Crop,
  PurchaseRequest,
  Quotation,
  Recommendation,
  RequestStatus,
  Supplier,
  Urgency,
} from "./types";

interface ViteEnv {
  VITE_API_BASE_URL?: string;
  VITE_TENANT_ID?: string;
  VITE_TEAM_ID?: string;
  VITE_ACTOR?: string;
}

const env = (import.meta as ImportMeta & { env?: ViteEnv }).env ?? {};
const rawBaseUrl = env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export const API_BASE_URL = rawBaseUrl.replace(/\/$/, "");
export const TENANT_ID = env.VITE_TENANT_ID ?? "tenant-yguazu";
export const TEAM_ID = env.VITE_TEAM_ID ?? "team-compras";
export const ACTOR = env.VITE_ACTOR ?? "ana.rojas@yguazu.coop.py";

type RequestOptions = RequestInit & {
  query?: Record<string, string | number | boolean | undefined | null>;
};

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  Object.entries(options.query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url.toString(), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      detail = await response.text();
    }
    throw new Error(detail || `API request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function toNumber(value: unknown, fallback = 0): number {
  if (value === null || value === undefined || value === "") return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function toDateInput(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function normalizeCategory(value?: string | null): Category {
  const normalized = (value ?? "fertilizante").toLowerCase();
  if (
    ["fertilizante", "semilla", "fitosanitario", "maquinaria", "repuesto", "combustible"].includes(
      normalized,
    )
  ) {
    return normalized as Category;
  }
  return "fertilizante";
}

function normalizeCrop(value?: string | null): Crop {
  const normalized = (value ?? "soja")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  if (["soja", "maiz", "trigo", "sorgo"].includes(normalized)) return normalized as Crop;
  return "soja";
}

function normalizeUrgency(value?: string | null): Urgency {
  if (value === "critica") return "critica";
  if (value === "urgente") return "alta";
  if (value === "normal") return "media";
  if (["baja", "media", "alta"].includes(value ?? "")) return value as Urgency;
  return "media";
}

function normalizeStatus(value?: string | null): RequestStatus {
  const map: Record<string, RequestStatus> = {
    draft: "borrador",
    in_quoting: "en_cotizacion",
    ready_for_review: "en_comparacion",
    recommended: "recomendada",
    approved: "aprobada",
    cancelled: "cerrada",
    closed: "cerrada",
  };
  return map[value ?? ""] ?? "borrador";
}

function categoryList(raw?: string | null): Category[] {
  return (raw ?? "")
    .split(",")
    .map((v) => normalizeCategory(v.trim()))
    .filter(Boolean);
}

export interface BackendRequestItem {
  item_id: string;
  description: string;
  quantity: string | number;
  unit: string;
  specifications?: string | null;
  target_unit_price?: string | number | null;
}

export interface BackendPurchaseRequest {
  tenant_id: string;
  team_id: string;
  requested_by: string;
  title: string;
  description?: string | null;
  category?: string | null;
  urgency: string;
  currency: string;
  budget_cap?: string | number | null;
  criteria_weights: { price: number; delivery: number; quality: number; terms: number };
  target_delivery_date: string;
  target_crop?: string | null;
  target_zafra?: string | null;
  fenological_window?: string | null;
  target_hectares?: string | number | null;
  delivery_department?: string | null;
  delivery_location?: string | null;
  current_stock_days?: number | null;
  items: BackendRequestItem[];
  request_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BackendSupplier {
  tenant_id: string;
  legal_name: string;
  ruc?: string | null;
  commercial_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  country: string;
  primary_categories?: string | null;
  primary_origin_countries?: string | null;
  is_importer: boolean;
  senave_registered: boolean;
  iso_certified: boolean;
  risk_tier: string;
  supplier_id: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface BackendQuotationItem {
  item_id: string;
  request_item_id?: string | null;
  description: string;
  quantity: string | number;
  unit_price: string | number;
  subtotal: string | number;
  brand?: string | null;
  origin?: string | null;
  presentation?: string | null;
  lead_time_days?: number | null;
}

export interface BackendQuotation {
  tenant_id: string;
  request_id: string;
  supplier_id: string;
  created_by: string;
  currency: string;
  exchange_rate_quoted?: string | number | null;
  incoterm?: string | null;
  includes_iva: boolean;
  iva_rate?: string | number | null;
  payment_terms?: string | null;
  total_amount: string | number;
  total_pyg_normalized?: string | number | null;
  lead_time_days: number;
  validity_until: string;
  warranty_months?: number | null;
  discount_pct?: string | number | null;
  terms_text?: string | null;
  raw_extracted_text?: string | null;
  extraction_confidence?: string | number | null;
  items: BackendQuotationItem[];
  quotation_id: string;
  anomaly_score?: string | number | null;
  anomaly_reason?: string | null;
  status: string;
  quality_flags: { code: string; message: string; field?: string | null }[];
  created_at: string;
  updated_at: string;
}

export interface ExtractedQuotation {
  supplier_legal_name?: string | null;
  supplier_ruc?: string | null;
  currency: string;
  exchange_rate_quoted?: string | number | null;
  incoterm?: string | null;
  includes_iva: boolean;
  iva_rate?: string | number | null;
  payment_terms?: string | null;
  total_amount: string | number;
  lead_time_days: number;
  validity_until_iso: string;
  warranty_months?: number | null;
  discount_pct?: string | number | null;
  items: {
    description: string;
    quantity: string | number;
    unit_price: string | number;
    subtotal: string | number;
    brand?: string | null;
    origin?: string | null;
    presentation?: string | null;
  }[];
  extraction_confidence: string | number;
  extraction_source: "llm" | "fallback";
}

export interface RecommendResponse {
  status: "completed" | "escalated";
  request_id: string;
  escalation_reason?: string | null;
  recommendation?: {
    recommended_quotation_id: string;
    recommended_supplier_id: string;
    decision_band: string;
    composite_score: string | number;
    urgency_score: string | number;
    offer_score: string | number;
    reasoning_markdown: string;
    source: "llm" | "fallback";
  } | null;
  recommendation_id?: string | null;
  weather_risk_score?: number | null;
  fx_rate_usd_pyg?: number | null;
  score_count: number;
}

export interface NegotiationMessage {
  message_text: string;
  tone: "cordial" | "formal" | "asertivo";
  target_improvements: Record<string, unknown>;
  source: "llm" | "fallback";
}

export function toUiRequest(request: BackendPurchaseRequest): PurchaseRequest {
  const total = request.items.reduce(
    (sum, item) => sum + toNumber(item.quantity) * toNumber(item.target_unit_price),
    0,
  );
  return {
    id: request.request_id,
    title: request.title,
    description: request.description ?? "",
    category: normalizeCategory(request.category),
    crop: normalizeCrop(request.target_crop),
    zafra: request.target_zafra ?? "2026/27",
    fenological_window: request.fenological_window ?? "N/A",
    hectares: toNumber(request.target_hectares),
    department: (request.delivery_department ?? "Itapua") as PurchaseRequest["department"],
    deadline: request.target_delivery_date,
    budget_pyg: toNumber(request.budget_cap, total),
    urgency: normalizeUrgency(request.urgency),
    weights: {
      precio: request.criteria_weights.price,
      plazo: request.criteria_weights.delivery,
      calidad: request.criteria_weights.quality,
      condiciones: request.criteria_weights.terms,
    },
    items: request.items.map((item) => ({
      id: item.item_id,
      description: item.description,
      qty: toNumber(item.quantity),
      unit: item.unit,
      spec: item.specifications ?? "",
      target_price_pyg: toNumber(item.target_unit_price),
    })),
    status: normalizeStatus(request.status),
    created_at: request.created_at,
    total_estimated_pyg: toNumber(request.budget_cap, total),
  };
}

export function toUiSupplier(supplier: BackendSupplier): Supplier {
  return {
    id: supplier.supplier_id,
    legal_name: supplier.legal_name,
    ruc: supplier.ruc ?? "N/A",
    primary_categories: categoryList(supplier.primary_categories),
    ml_p_on_time: supplier.risk_tier === "low" ? 0.88 : supplier.risk_tier === "high" ? 0.58 : 0.74,
    on_time_rate: supplier.risk_tier === "low" ? 0.91 : supplier.risk_tier === "high" ? 0.66 : 0.8,
    quotations_received: 0,
    awards: 0,
    last_activity: supplier.updated_at,
  };
}

export function toUiQuotation(quotation: BackendQuotation): Quotation {
  const anomalyScore = toNumber(quotation.anomaly_score);
  const total = toNumber(quotation.total_pyg_normalized ?? quotation.total_amount);
  const mlScore = Math.max(45, Math.min(94, Math.round(86 - anomalyScore * 35)));
  return {
    id: quotation.quotation_id,
    request_id: quotation.request_id,
    supplier_id: quotation.supplier_id,
    total_pyg: total,
    delivery_days: quotation.lead_time_days,
    warranty_months: quotation.warranty_months ?? 0,
    payment_terms: quotation.payment_terms ?? "-",
    ml_score: mlScore,
    ml_p_on_time: mlScore / 100,
    anomaly: anomalyScore >= 0.6 || quotation.status === "quarantined",
    anomaly_reason:
      quotation.anomaly_reason ??
      quotation.quality_flags.map((flag) => flag.message).join("; ") ??
      undefined,
    status: quotation.status === "validated" ? "validada" : "pendiente",
    items: quotation.items.map((item) => ({
      item_id: item.request_item_id ?? item.item_id,
      unit_price_pyg: toNumber(item.unit_price),
      qty: toNumber(item.quantity),
    })),
    notes: quotation.terms_text ?? undefined,
  };
}

export function toUiRecommendation(response: RecommendResponse): Recommendation | null {
  const recommendation = response.recommendation;
  if (!recommendation) return null;
  return {
    request_id: response.request_id,
    recommended_supplier_id: recommendation.recommended_supplier_id,
    decision_band:
      toNumber(recommendation.composite_score) >= 75
        ? "alta_confianza"
        : toNumber(recommendation.composite_score) >= 55
          ? "media_confianza"
          : "baja_confianza",
    composite_score: Math.round(toNumber(recommendation.composite_score)),
    urgency_score: {
      total: Math.round(toNumber(recommendation.urgency_score)),
      weather: Math.round(response.weather_risk_score ?? 40),
      delivery: Math.round(toNumber(recommendation.urgency_score)),
      volatility: response.fx_rate_usd_pyg ? 55 : 40,
    },
    offer_score: {
      total: Math.round(toNumber(recommendation.offer_score)),
      supplier: Math.round(toNumber(recommendation.offer_score)),
      terms: Math.round(toNumber(recommendation.offer_score) * 0.9),
      delivery_risk: Math.max(0, 100 - Math.round(toNumber(recommendation.offer_score))),
    },
    justification_md: recommendation.reasoning_markdown,
    alternatives_md: `- Recommendation source: **${recommendation.source}**\n- Scores evaluated: **${response.score_count}** quotations`,
    risks_md: response.escalation_reason
      ? `- Escalation: **${response.escalation_reason}**`
      : "- Review supplier terms, validity date, and delivery feasibility before award.",
  };
}

export const procurementApi = {
  listRequests: () =>
    apiRequest<BackendPurchaseRequest[]>("/api/v1/procurement/requests", {
      query: { tenant_id: TENANT_ID, team_id: TEAM_ID },
    }),
  getRequest: (requestId: string) =>
    apiRequest<BackendPurchaseRequest>(`/api/v1/procurement/requests/${requestId}`, {
      query: { tenant_id: TENANT_ID },
    }),
  createRequest: (payload: unknown) =>
    apiRequest<BackendPurchaseRequest>("/api/v1/procurement/requests", {
      method: "POST",
      query: { actor: ACTOR },
      body: JSON.stringify(payload),
    }),
  transitionRequest: (requestId: string, newStatus: string) =>
    apiRequest<BackendPurchaseRequest>(`/api/v1/procurement/requests/${requestId}/transition`, {
      method: "POST",
      query: { tenant_id: TENANT_ID, new_status: newStatus, actor: ACTOR },
      body: JSON.stringify({}),
    }),
  listSuppliers: () =>
    apiRequest<BackendSupplier[]>("/api/v1/procurement/suppliers", {
      query: { tenant_id: TENANT_ID },
    }),
  createSupplier: (payload: unknown) =>
    apiRequest<BackendSupplier>("/api/v1/procurement/suppliers", {
      method: "POST",
      query: { actor: ACTOR },
      body: JSON.stringify(payload),
    }),
  listQuotations: (requestId: string, onlyValidated = false) =>
    apiRequest<BackendQuotation[]>(`/api/v1/procurement/requests/${requestId}/quotations`, {
      query: { tenant_id: TENANT_ID, only_validated: onlyValidated },
    }),
  extractQuotation: (requestId: string, rawText: string) =>
    apiRequest<ExtractedQuotation>("/api/v1/procurement/quotations/extract", {
      method: "POST",
      body: JSON.stringify({ tenant_id: TENANT_ID, request_id: requestId, raw_text: rawText }),
    }),
  uploadQuotation: (payload: unknown) =>
    apiRequest<BackendQuotation>("/api/v1/procurement/quotations", {
      method: "POST",
      query: { actor: ACTOR },
      body: JSON.stringify(payload),
    }),
  recommendRequest: (requestId: string) =>
    apiRequest<RecommendResponse>(`/api/v1/procurement/requests/${requestId}/recommend`, {
      method: "POST",
      query: { tenant_id: TENANT_ID },
      body: JSON.stringify({}),
    }),
  negotiateQuotation: (quotationId: string, payload: unknown) =>
    apiRequest<NegotiationMessage>(`/api/v1/procurement/quotations/${quotationId}/negotiate`, {
      method: "POST",
      body: JSON.stringify({ tenant_id: TENANT_ID, ...(payload as object) }),
    }),
};

export function buildRequestPayload(input: {
  title: string;
  description: string;
  category: string;
  crop: string;
  zafra: string;
  fenologicalWindow: string;
  hectares: number;
  department: string;
  deadline: string;
  budget: number;
  urgency: string;
  weights: { precio: number; plazo: number; calidad: number; condiciones: number };
  items: { description: string; qty: number; unit: string; spec: string; target: number }[];
}) {
  return {
    tenant_id: TENANT_ID,
    team_id: TEAM_ID,
    requested_by: ACTOR,
    title: input.title,
    description: input.description,
    category: input.category.toLowerCase(),
    urgency:
      input.urgency === "critica" ? "critica" : input.urgency === "alta" ? "urgente" : "normal",
    currency: "PYG",
    budget_cap: input.budget,
    criteria_weights: {
      price: input.weights.precio,
      delivery: input.weights.plazo,
      quality: input.weights.calidad,
      terms: input.weights.condiciones,
    },
    target_delivery_date:
      input.deadline || toDateInput(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)),
    target_crop: input.crop.toLowerCase(),
    target_zafra: input.zafra,
    fenological_window: input.fenologicalWindow,
    target_hectares: input.hectares,
    delivery_department: input.department,
    current_stock_days: input.urgency === "critica" ? 3 : input.urgency === "alta" ? 7 : 20,
    items: input.items
      .filter((item) => item.description.trim() && item.qty > 0)
      .map((item, position) => ({
        description: item.description,
        quantity: item.qty,
        unit: item.unit,
        specifications: item.spec,
        target_unit_price: item.target || null,
        position,
      })),
  };
}

export function buildQuotationPayload(input: {
  requestId: string;
  supplierId: string;
  rawText: string;
  extracted: ExtractedQuotation;
}) {
  const items = input.extracted.items.map((item) => ({
    description: item.description,
    quantity: toNumber(item.quantity, 1),
    unit_price: toNumber(item.unit_price),
    subtotal: toNumber(item.subtotal, toNumber(item.quantity, 1) * toNumber(item.unit_price)),
    brand: item.brand ?? null,
    origin: item.origin ?? null,
    presentation: item.presentation ?? null,
  }));
  return {
    tenant_id: TENANT_ID,
    request_id: input.requestId,
    supplier_id: input.supplierId,
    created_by: ACTOR,
    currency: input.extracted.currency,
    exchange_rate_quoted: input.extracted.exchange_rate_quoted ?? null,
    incoterm: input.extracted.incoterm ?? null,
    includes_iva: input.extracted.includes_iva,
    iva_rate: input.extracted.iva_rate ?? null,
    payment_terms: input.extracted.payment_terms ?? null,
    total_amount: toNumber(input.extracted.total_amount),
    total_pyg_normalized:
      input.extracted.currency === "PYG" ? toNumber(input.extracted.total_amount) : null,
    lead_time_days: input.extracted.lead_time_days,
    validity_until: input.extracted.validity_until_iso,
    warranty_months: input.extracted.warranty_months ?? null,
    discount_pct: input.extracted.discount_pct ?? null,
    raw_extracted_text: input.rawText,
    extraction_confidence: toNumber(input.extracted.extraction_confidence),
    items,
  };
}
