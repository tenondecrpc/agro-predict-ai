import { useApp } from "@/lib/agro/app-context";
import type { Role } from "@/lib/agro/types";
import { ChevronDown, MapPin, Wheat, User } from "lucide-react";
import { useState } from "react";

const ROLES: Role[] = ["Solicitante", "Comprador", "Aprobador", "Director"];

export function Header() {
  const { role, setRole, user } = useApp();
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 bg-background/80 backdrop-blur border-b border-border">
      <div className="px-6 py-3 flex items-center gap-4">
        <div className="min-w-0">
          <h1 className="text-lg font-bold tracking-tight text-foreground">
            Cooperativa Yguazú
          </h1>
          <p className="text-[12px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
            <MapPin className="size-3" aria-hidden />
            Itapúa, Paraguay
            <span className="opacity-50">·</span>
            <Wheat className="size-3" aria-hidden />
            Campaña 2026/27
          </p>
        </div>

        <div className="ml-auto flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
            <div className="size-8 rounded-full bg-secondary flex items-center justify-center">
              <User className="size-4 text-secondary-foreground" aria-hidden />
            </div>
            <div className="leading-tight">
              <div className="text-foreground font-semibold text-[13px]">{user.name}</div>
              <div className="text-[11px]">{user.email}</div>
            </div>
          </div>

          <div className="relative">
            <button
              type="button"
              onClick={() => setOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full bg-primary-gradient text-primary-foreground px-3.5 py-1.5 text-sm font-semibold shadow-soft hover:shadow-glow transition-shadow"
              aria-haspopup="menu"
              aria-expanded={open}
            >
              <span className="size-2 rounded-full bg-primary-glow shadow-[0_0_8px] shadow-primary-glow" aria-hidden />
              {role}
              <ChevronDown className="size-4" aria-hidden />
            </button>
            {open && (
              <div
                role="menu"
                className="absolute right-0 mt-2 w-44 rounded-lg border border-border bg-popover shadow-card overflow-hidden"
              >
                {ROLES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    role="menuitemradio"
                    aria-checked={r === role}
                    onClick={() => {
                      setRole(r);
                      setOpen(false);
                    }}
                    className={[
                      "w-full text-left px-3 py-2 text-sm hover:bg-secondary transition-colors flex items-center gap-2",
                      r === role ? "bg-secondary/60 text-primary font-semibold" : "text-foreground",
                    ].join(" ")}
                  >
                    {r === role && (
                      <span className="size-1.5 rounded-full bg-primary" aria-hidden />
                    )}
                    <span className={r === role ? "" : "ml-3.5"}>{r}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
