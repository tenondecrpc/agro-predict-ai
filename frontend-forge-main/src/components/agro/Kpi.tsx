import type { ReactNode } from "react";
import { Card } from "./Card";

export function Kpi({
  label,
  value,
  sub,
  icon,
  tone = "primary",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  tone?: "primary" | "earth" | "warning" | "info" | "success";
}) {
  const tint =
    tone === "primary"
      ? "bg-primary/10 text-primary"
      : tone === "earth"
      ? "bg-earth/15 text-earth"
      : tone === "warning"
      ? "bg-warning/15 text-warning-foreground"
      : tone === "info"
      ? "bg-info/12 text-info"
      : "bg-success/12 text-success";
  return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        {icon && (
          <div className={`size-10 rounded-xl flex items-center justify-center ${tint}`}>
            {icon}
          </div>
        )}
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            {label}
          </div>
          <div className="mt-1 text-2xl font-bold tracking-tight tabular text-foreground">
            {value}
          </div>
          {sub && <div className="mt-1 text-xs text-muted-foreground">{sub}</div>}
        </div>
      </div>
    </Card>
  );
}
