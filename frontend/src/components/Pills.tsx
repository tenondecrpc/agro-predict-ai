import type { Urgency, Status } from "@/lib/types";
import { AlertTriangle, CheckCircle2, Clock, FileEdit, Gavel, XCircle, Eye } from "lucide-react";

export function UrgencyPill({ value }: { value: Urgency }) {
  const map = {
    baja: { c: "bg-muted text-muted-foreground ring-border", label: "Baja" },
    media: { c: "bg-info/15 text-info ring-info/30", label: "Media" },
    alta: { c: "bg-warning/20 text-warning-foreground ring-warning/40", label: "Alta" },
    critica: { c: "bg-destructive/15 text-destructive ring-destructive/30", label: "Crítica" },
  } as const;
  const cfg = map[value];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${cfg.c}`}>
      {value === "critica" || value === "alta" ? <AlertTriangle className="h-3 w-3" aria-hidden /> : <Clock className="h-3 w-3" aria-hidden />}
      {cfg.label}
    </span>
  );
}

export function StatusPill({ value }: { value: Status }) {
  const map: Record<Status, { c: string; label: string; Icon: typeof Clock }> = {
    borrador: { c: "bg-muted text-muted-foreground ring-border", label: "Borrador", Icon: FileEdit },
    publicada: { c: "bg-info/15 text-info ring-info/30", label: "Publicada", Icon: Eye },
    en_evaluacion: { c: "bg-warning/20 text-warning-foreground ring-warning/40", label: "En evaluación", Icon: Clock },
    adjudicada: { c: "bg-success/20 text-success-foreground ring-success/40", label: "Adjudicada", Icon: CheckCircle2 },
    cerrada: { c: "bg-primary-soft text-primary ring-primary/30", label: "Cerrada", Icon: Gavel },
    cancelada: { c: "bg-destructive/15 text-destructive ring-destructive/30", label: "Cancelada", Icon: XCircle },
  };
  const cfg = map[value];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${cfg.c}`}>
      <cfg.Icon className="h-3 w-3" aria-hidden /> {cfg.label}
    </span>
  );
}

export function MLBand({ score }: { score: number }) {
  const tone = score >= 80 ? "bg-success/20 text-success-foreground ring-success/40" : score >= 60 ? "bg-warning/20 text-warning-foreground ring-warning/40" : "bg-destructive/15 text-destructive ring-destructive/30";
  const label = score >= 80 ? "Alta" : score >= 60 ? "Media" : "Baja";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${tone} num`}>
      ML {score} · {label}
    </span>
  );
}
