import { createContext, useContext, useState, type ReactNode } from "react";
import type { Role } from "./types";

interface AppCtx {
  role: Role;
  setRole: (r: Role) => void;
  user: { name: string; email: string };
}

const Ctx = createContext<AppCtx | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>("Comprador");
  return (
    <Ctx.Provider
      value={{
        role,
        setRole,
        user: { name: "Ana Rojas", email: "comprador@yguazu.coop.py" },
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useApp() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
