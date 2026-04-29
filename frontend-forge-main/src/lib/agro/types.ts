export type Role = "Solicitante" | "Comprador" | "Aprobador" | "Director";

export type RequestStatus =
  | "borrador"
  | "publicada"
  | "en_cotizacion"
  | "en_comparacion"
  | "recomendada"
  | "aprobada"
  | "adjudicada"
  | "cerrada";

export type Urgency = "baja" | "media" | "alta" | "critica";
export type Category =
  | "fertilizante"
  | "semilla"
  | "fitosanitario"
  | "maquinaria"
  | "repuesto"
  | "combustible";
export type Crop = "soja" | "maiz" | "trigo" | "sorgo";
export type Department =
  | "Itapua"
  | "Alto Parana"
  | "Caaguazu"
  | "Canindeyu"
  | "San Pedro";

export interface Item {
  id: string;
  description: string;
  qty: number;
  unit: string;
  spec: string;
  target_price_pyg: number;
}

export interface Weights {
  precio: number;
  plazo: number;
  calidad: number;
  condiciones: number;
}

export interface PurchaseRequest {
  id: string;
  title: string;
  description: string;
  category: Category;
  crop: Crop;
  zafra: string;
  fenological_window: string;
  hectares: number;
  department: Department;
  deadline: string; // ISO
  budget_pyg: number;
  urgency: Urgency;
  weights: Weights;
  items: Item[];
  status: RequestStatus;
  created_at: string;
  total_estimated_pyg: number;
}

export interface Quotation {
  id: string;
  request_id: string;
  supplier_id: string;
  total_pyg: number;
  delivery_days: number;
  warranty_months: number;
  payment_terms: string;
  ml_score: number; // 0-100
  ml_p_on_time: number; // 0-1
  anomaly: boolean;
  anomaly_reason?: string;
  status: "validada" | "pendiente";
  items: { item_id: string; unit_price_pyg: number; qty: number }[];
  notes?: string;
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
  decision_band: "alta_confianza" | "media_confianza" | "baja_confianza";
  composite_score: number;
  urgency_score: { total: number; weather: number; delivery: number; volatility: number };
  offer_score: { total: number; supplier: number; terms: number; delivery_risk: number };
  justification_md: string;
  alternatives_md: string;
  risks_md: string;
}
