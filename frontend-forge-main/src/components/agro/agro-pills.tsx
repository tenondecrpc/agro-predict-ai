import { Pill } from "./Pill";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Sprout,
  Wheat,
  Cloud,
  Truck,
  Droplets,
  Wrench,
  Fuel,
} from "lucide-react";
import type {
  Category,
  Crop,
  RequestStatus,
  Urgency,
} from "@/lib/agro/types";

export function UrgencyPill({ value }: { value: Urgency }) {
  const map: Record<Urgency, { tone: any; label: string }> = {
    baja: { tone: "neutral", label: "Baja" },
    media: { tone: "info", label: "Media" },
    alta: { tone: "warning", label: "Alta" },
    critica: { tone: "danger", label: "Crítica" },
  };
  const m = map[value];
  return (
    <Pill tone={m.tone} icon={<Clock className="size-3" aria-hidden />}>
      {m.label}
    </Pill>
  );
}

export function StatusPill({ value }: { value: RequestStatus }) {
  const map: Record<RequestStatus, { tone: any; label: string }> = {
    borrador: { tone: "neutral", label: "Borrador" },
    publicada: { tone: "info", label: "Publicada" },
    en_cotizacion: { tone: "info", label: "En cotización" },
    en_comparacion: { tone: "primary", label: "En comparación" },
    recomendada: { tone: "primary", label: "Recomendada" },
    aprobada: { tone: "success", label: "Aprobada" },
    adjudicada: { tone: "success", label: "Adjudicada" },
    cerrada: { tone: "neutral", label: "Cerrada" },
  };
  const m = map[value];
  return <Pill tone={m.tone}>{m.label}</Pill>;
}

export function CropIcon({ value, className = "size-4" }: { value: Crop; className?: string }) {
  const Icon = value === "soja" ? Sprout : value === "maiz" ? Wheat : value === "trigo" ? Wheat : Sprout;
  const label = { soja: "Soja", maiz: "Maíz", trigo: "Trigo", sorgo: "Sorgo" }[value];
  return (
    <span className="inline-flex items-center gap-1 text-foreground/80">
      <Icon className={className} aria-hidden />
      <span className="text-xs font-medium">{label}</span>
    </span>
  );
}

export function CategoryIcon({ value }: { value: Category }) {
  const Icon =
    value === "fertilizante"
      ? Sprout
      : value === "fitosanitario"
      ? Droplets
      : value === "semilla"
      ? Wheat
      : value === "maquinaria"
      ? Truck
      : value === "combustible"
      ? Fuel
      : Wrench;
  return <Icon className="size-4 text-earth" aria-hidden />;
}

export function MlBand({ score }: { score: number }) {
  const tone = score >= 80 ? "success" : score >= 60 ? "warning" : "danger";
  const label = score >= 80 ? "Alto" : score >= 60 ? "Medio" : "Bajo";
  const Icon = score >= 80 ? CheckCircle2 : AlertTriangle;
  return (
    <Pill tone={tone as any} icon={<Icon className="size-3" aria-hidden />}>
      ML {score} · {label}
    </Pill>
  );
}

export function WeatherBadge() {
  return (
    <Pill tone="info" icon={<Cloud className="size-3" aria-hidden />}>
      Lluvia días 8–10
    </Pill>
  );
}
