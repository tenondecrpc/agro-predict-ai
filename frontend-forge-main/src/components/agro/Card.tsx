import type { ReactNode } from "react";

export function Card({
  children,
  className = "",
  as: As = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "section" | "article";
}) {
  return (
    <As
      className={[
        "rounded-2xl bg-card border border-border shadow-soft",
        className,
      ].join(" ")}
    >
      {children}
    </As>
  );
}
