import { createContext, useContext, useState, type ReactNode } from "react";

export type Role = "Solicitante" | "Comprador" | "Aprobador" | "Director";

const RoleCtx = createContext<{ role: Role; setRole: (r: Role) => void }>({
  role: "Comprador",
  setRole: () => {},
});

export function RoleProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role>("Comprador");
  return <RoleCtx.Provider value={{ role, setRole }}>{children}</RoleCtx.Provider>;
}

export const useRole = () => useContext(RoleCtx);

export const ROLES: Role[] = ["Solicitante", "Comprador", "Aprobador", "Director"];
