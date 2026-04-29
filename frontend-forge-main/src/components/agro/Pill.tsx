import type { ReactNode } from "react";

type Tone = "success" | "warning" | "danger" | "info" | "neutral" | "earth" | "primary";

const TONE: Record<Tone, string> = {
  success: "bg-success/12 text-success border-success/30",
  warning: "bg-warning/15 text-warning-foreground border-warning/40",
  danger: "bg-destructive/12 text-destructive border-destructive/30",
  info: "bg-info/12 text-info border-info/30",
  neutral: "bg-secondary text-secondary-foreground border-border",
  earth: "bg-earth/15 text-earth border-earth/30",
  primary: "bg-primary/10 text-primary border-primary/25",
};

export function Pill({
  children,
  tone = "neutral",
  icon,
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold whitespace-nowrap",
        TONE[tone],
        className,
      ].join(" ")}
    >
      {icon}
      {children}
    </span>
  );
}
