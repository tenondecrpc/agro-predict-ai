export type Urgency = "baja" | "media" | "alta" | "critica";
export type Status = "borrador" | "publicada" | "en_evaluacion" | "adjudicada" | "cerrada" | "cancelada";
export type Crop = "soja" | "maiz" | "trigo" | "sorgo" | "girasol" | "arroz";
export type Category = "fertilizante" | "semilla" | "fitosanitario" | "maquinaria" | "repuesto" | "combustible";

export interface PRItem {
  id: string;
  description: string;
  quantity: number;
  unit: string;
  specs?: string;
  target_price?: number;
}

export interface PurchaseRequest {
  id: string;
  title: string;
  description?: string;
  category: Category;
  target_crop: Crop;
  zafra: string;
  fenological_window: string;
  hectares: number;
  department: string;
  deadline: string;
  budget_pyg: number;
  urgency: Urgency;
  status: Status;
  weights: { precio: number; plazo: number; calidad: number; condiciones: number };
  items: PRItem[];
  created_at: string;
  created_by: string;
}

export interface Quotation {
  id: string;
  request_id: string;
  supplier_id: string;
  supplier_name: string;
  total_pyg: number;
  total_normalized_pyg: number;
  currency: "PYG" | "USD";
  delivery_days: number;
  warranty_months: number;
  payment_terms: string;
  ml_score: number;            // 0-100
  ml_p_on_time: number;        // 0-1
  anomaly_flag: boolean;
  anomaly_reason?: string;
  confidence: number;          // 0-1 LLM extraction confidence
  items: Array<{ description: string; quantity: number; unit_price_pyg: number; total: number }>;
  created_at: string;
}

export interface Supplier {
  id: string;
  legal_name: string;
  ruc: string;
  primary_categories: Category[];
  ml_p_on_time: number;
  on_time_rate: number;
  quotations_received: number;
  awards: number;
  last_activity: string;
}

export interface Recommendation {
  request_id: string;
  recommended_supplier_id: string;
  recommended_supplier_name: string;
  decision_band: "alta_confianza" | "media_confianza" | "revisar";
  composite_score: number;
  urgency_score: { total: number; weather: number; delivery: number; volatility: number };
  offer_score: { total: number; supplier: number; terms: number; delivery_risk: number };
  justification_md: string;
  alternatives_md: string;
  risks_md: string;
}

export interface NegotiationMessage {
  supplier_id: string;
  subject: string;
  body: string;
}
