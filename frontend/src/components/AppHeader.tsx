import { useRole, ROLES, type Role } from "@/lib/role";
import { ChevronDown, MapPin } from "lucide-react";
import { useState } from "react";

export function AppHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  const { role, setRole } = useRole();
  const [open, setOpen] = useState(false);

  return (
    <header className="border-b border-border bg-card/70 backdrop-blur-sm">
      <div className="px-6 lg:px-8 py-4 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground">{title}</h1>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
            <MapPin className="h-3 w-3" aria-hidden />
            <span>{subtitle ?? "Cooperativa Yguazú · Itapúa, Paraguay · Campaña 2026/27"}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:flex flex-col items-end text-xs">
            <span className="font-semibold text-foreground">Ana Rojas</span>
            <span className="text-muted-foreground">comprador@yguazu.coop.py</span>
          </div>

          <div className="relative">
            <button
              onClick={() => setOpen((v) => !v)}
              className="flex items-center gap-1.5 rounded-full bg-primary/10 text-primary px-3 py-1.5 text-xs font-semibold ring-1 ring-primary/20 hover:bg-primary/15 outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`Rol actual: ${role}. Cambiar rol`}
            >
              {role}
              <ChevronDown className="h-3.5 w-3.5" aria-hidden />
            </button>
            {open && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
                <div className="absolute right-0 mt-2 w-44 rounded-lg border border-border bg-popover shadow-lg z-20 overflow-hidden">
                  {ROLES.map((r) => (
                    <button
                      key={r}
                      onClick={() => {
                        setRole(r as Role);
                        setOpen(false);
                      }}
                      className={`w-full text-left px-3 py-2 text-sm hover:bg-accent ${
                        r === role ? "bg-primary/10 text-primary font-semibold" : ""
                      }`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
