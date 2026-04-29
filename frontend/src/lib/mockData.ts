import type { PurchaseRequest, Quotation, Supplier, Recommendation } from "./types";

export const SUPPLIERS: Supplier[] = [
  {
    id: "sup-tecnomyl", legal_name: "Tecnomyl SA", ruc: "80012345-1",
    primary_categories: ["fertilizante", "fitosanitario"],
    ml_p_on_time: 0.92, on_time_rate: 0.94, quotations_received: 47, awards: 21,
    last_activity: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    id: "sup-agrofertil", legal_name: "Agrofertil SA", ruc: "80023456-2",
    primary_categories: ["fertilizante", "semilla"],
    ml_p_on_time: 0.85, on_time_rate: 0.88, quotations_received: 39, awards: 14,
    last_activity: new Date(Date.now() - 1 * 86400000).toISOString(),
  },
  {
    id: "sup-atlantic", legal_name: "Atlantic Comercio Agroindustrial", ruc: "80034567-3",
    primary_categories: ["fertilizante"],
    ml_p_on_time: 0.71, on_time_rate: 0.74, quotations_received: 22, awards: 6,
    last_activity: new Date(Date.now() - 5 * 86400000).toISOString(),
  },
  {
    id: "sup-glymax", legal_name: "Glymax Paraguay", ruc: "80045678-4",
    primary_categories: ["fitosanitario", "fertilizante"],
    ml_p_on_time: 0.81, on_time_rate: 0.83, quotations_received: 31, awards: 11,
    last_activity: new Date(Date.now() - 3 * 86400000).toISOString(),
  },
  {
    id: "sup-ciabay", legal_name: "Ciabay SA", ruc: "80056789-5",
    primary_categories: ["semilla", "fitosanitario"],
    ml_p_on_time: 0.78, on_time_rate: 0.80, quotations_received: 18, awards: 7,
    last_activity: new Date(Date.now() - 8 * 86400000).toISOString(),
  },
];

export const REQUESTS: PurchaseRequest[] = [
  {
    id: "pr-001",
    title: "Compra de 800 ton de urea 46% para zafra soja 26/27",
    description: "Cobertura de necesidades de fertilización nitrogenada para socios productores de Itapúa. Entrega escalonada en depósito Yguazú.",
    category: "fertilizante",
    target_crop: "soja",
    zafra: "2026/27",
    fenological_window: "Pre-siembra · V2-V4",
    hectares: 12500,
    department: "Itapúa",
    deadline: new Date(Date.now() + 18 * 86400000).toISOString(),
    budget_pyg: 5_600_000_000,
    urgency: "alta",
    status: "en_evaluacion",
    weights: { precio: 45, plazo: 25, calidad: 20, condiciones: 10 },
    items: [
      { id: "it-1", description: "Urea granulada 46% N", quantity: 800, unit: "ton", specs: "Bolsa 50kg, libre de biuret", target_price: 6_800_000 },
    ],
    created_at: new Date(Date.now() - 4 * 86400000).toISOString(),
    created_by: "Ana Rojas",
  },
  {
    id: "pr-002",
    title: "Semilla de soja BMX Icono IPRO — 200 ton",
    category: "semilla",
    target_crop: "soja",
    zafra: "2026/27",
    fenological_window: "Siembra octubre",
    hectares: 4000,
    department: "Itapúa",
    deadline: new Date(Date.now() + 32 * 86400000).toISOString(),
    budget_pyg: 2_100_000_000,
    urgency: "media",
    status: "publicada",
    weights: { precio: 35, plazo: 20, calidad: 35, condiciones: 10 },
    items: [
      { id: "it-1", description: "Semilla soja BMX Icono IPRO", quantity: 200, unit: "ton", target_price: 10_000_000 },
    ],
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
    created_by: "Ana Rojas",
  },
  {
    id: "pr-003",
    title: "Glifosato 48% — 30.000 lt para barbecho químico",
    category: "fitosanitario",
    target_crop: "soja",
    zafra: "2026/27",
    fenological_window: "Barbecho",
    hectares: 8000,
    department: "Alto Paraná",
    deadline: new Date(Date.now() + 9 * 86400000).toISOString(),
    budget_pyg: 1_350_000_000,
    urgency: "critica",
    status: "publicada",
    weights: { precio: 50, plazo: 30, calidad: 15, condiciones: 5 },
    items: [
      { id: "it-1", description: "Glifosato 48% SL", quantity: 30000, unit: "lt", target_price: 42_000 },
    ],
    created_at: new Date(Date.now() - 1 * 86400000).toISOString(),
    created_by: "Ana Rojas",
  },
  {
    id: "pr-004",
    title: "Repuestos pulverizador autopropulsado Jacto Uniport",
    category: "repuesto",
    target_crop: "soja",
    zafra: "2026/27",
    fenological_window: "Mantenimiento",
    hectares: 0,
    department: "Itapúa",
    deadline: new Date(Date.now() + 22 * 86400000).toISOString(),
    budget_pyg: 180_000_000,
    urgency: "baja",
    status: "publicada",
    weights: { precio: 30, plazo: 20, calidad: 40, condiciones: 10 },
    items: [
      { id: "it-1", description: "Kit boquillas + filtros + bomba", quantity: 1, unit: "kit" },
    ],
    created_at: new Date(Date.now() - 6 * 86400000).toISOString(),
    created_by: "Ana Rojas",
  },
  {
    id: "pr-005",
    title: "Combustible Diesel S10 — 120.000 lt para cosecha trigo",
    category: "combustible",
    target_crop: "trigo",
    zafra: "2026",
    fenological_window: "Cosecha",
    hectares: 6500,
    department: "Itapúa",
    deadline: new Date(Date.now() + 5 * 86400000).toISOString(),
    budget_pyg: 980_000_000,
    urgency: "alta",
    status: "adjudicada",
    weights: { precio: 60, plazo: 30, calidad: 5, condiciones: 5 },
    items: [
      { id: "it-1", description: "Diesel S10 a granel", quantity: 120000, unit: "lt", target_price: 8_100 },
    ],
    created_at: new Date(Date.now() - 12 * 86400000).toISOString(),
    created_by: "Ana Rojas",
  },
];

export const QUOTATIONS: Quotation[] = [
  {
    id: "q-001", request_id: "pr-001", supplier_id: "sup-tecnomyl", supplier_name: "Tecnomyl SA",
    total_pyg: 5_280_000_000, total_normalized_pyg: 5_280_000_000, currency: "PYG",
    delivery_days: 14, warranty_months: 12, payment_terms: "30/60/90 días",
    ml_score: 88, ml_p_on_time: 0.92, anomaly_flag: false, confidence: 0.95,
    items: [{ description: "Urea 46% N", quantity: 800, unit_price_pyg: 6_600_000, total: 5_280_000_000 }],
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
  },
  {
    id: "q-002", request_id: "pr-001", supplier_id: "sup-agrofertil", supplier_name: "Agrofertil SA",
    total_pyg: 5_440_000_000, total_normalized_pyg: 5_440_000_000, currency: "PYG",
    delivery_days: 18, warranty_months: 12, payment_terms: "Contado 5% desc / 60d",
    ml_score: 78, ml_p_on_time: 0.85, anomaly_flag: false, confidence: 0.92,
    items: [{ description: "Urea 46% N", quantity: 800, unit_price_pyg: 6_800_000, total: 5_440_000_000 }],
    created_at: new Date(Date.now() - 3 * 86400000).toISOString(),
  },
  {
    id: "q-003", request_id: "pr-001", supplier_id: "sup-atlantic", supplier_name: "Atlantic Comercio Agroindustrial",
    total_pyg: 4_472_000_000, total_normalized_pyg: 4_472_000_000, currency: "PYG",
    delivery_days: 25, warranty_months: 6, payment_terms: "Anticipo 50%",
    ml_score: 52, ml_p_on_time: 0.71, anomaly_flag: true,
    anomaly_reason: "Precio 18% por debajo del promedio de mercado (Gs. 6.800.000/ton). Garantía menor a la habitual. Posible producto de origen no certificado o stock antiguo.",
    confidence: 0.74,
    items: [{ description: "Urea 46% N", quantity: 800, unit_price_pyg: 5_590_000, total: 4_472_000_000 }],
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
  {
    id: "q-004", request_id: "pr-001", supplier_id: "sup-glymax", supplier_name: "Glymax Paraguay",
    total_pyg: 5_360_000_000, total_normalized_pyg: 5_360_000_000, currency: "PYG",
    delivery_days: 16, warranty_months: 9, payment_terms: "30/60 días",
    ml_score: 74, ml_p_on_time: 0.81, anomaly_flag: false, confidence: 0.90,
    items: [{ description: "Urea 46% N", quantity: 800, unit_price_pyg: 6_700_000, total: 5_360_000_000 }],
    created_at: new Date(Date.now() - 2 * 86400000).toISOString(),
  },
];

export const RECOMMENDATION: Recommendation = {
  request_id: "pr-001",
  recommended_supplier_id: "sup-tecnomyl",
  recommended_supplier_name: "Tecnomyl SA",
  decision_band: "alta_confianza",
  composite_score: 87,
  urgency_score: { total: 72, weather: 78, delivery: 70, volatility: 68 },
  offer_score: { total: 89, supplier: 92, terms: 88, delivery_risk: 85 },
  justification_md: `**Tecnomyl SA** es la opción recomendada con **alta confianza** para esta solicitud crítica de 800 ton de urea.

- **Mejor balance precio-riesgo:** segundo precio más bajo (Gs. 5.280M) con la mayor probabilidad de entrega a tiempo (92%).
- **Plazo competitivo:** 14 días, dentro de la ventana fenológica V2-V4 sin comprometer la zafra.
- **Garantía estándar de 12 meses** y términos de pago escalonados 30/60/90 favorables al flujo de caja cooperativo.
- **Histórico fuerte:** 21 adjudicaciones previas con 94% de cumplimiento on-time.`,
  alternatives_md: `- **Glymax Paraguay** (score 74): precio similar pero menor histórico y garantía de solo 9 meses.
- **Agrofertil SA** (score 78): precio 3% más alto y plazo de 18 días, ajustado para la ventana.
- **Atlantic Comercio Agroindustrial: descartado por anomalía** — precio 18% bajo mercado sugiere riesgo de calidad o stock antiguo no certificado.`,
  risks_md: `- ⚠️ **Volatilidad de urea:** mercado internacional con +6% mensual; recomendado cerrar en próximas 72h.
- ⚠️ **Pronóstico clima Itapúa:** lluvias moderadas días 8-12 podrían retrasar logística terrestre.
- ✓ Riesgo proveedor bajo: Tecnomyl con score ML on-time 92%.`,
};
