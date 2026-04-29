export const fmtPYG = (n: number) =>
  "Gs. " + new Intl.NumberFormat("es-PY", { maximumFractionDigits: 0 }).format(Math.round(n));

export const fmtNumber = (n: number, digits = 0) =>
  new Intl.NumberFormat("es-PY", { maximumFractionDigits: digits }).format(n);

export const fmtPct = (n: number, digits = 0) =>
  new Intl.NumberFormat("es-PY", { style: "percent", maximumFractionDigits: digits }).format(n);

export const daysUntil = (iso: string) => {
  const ms = new Date(iso).getTime() - Date.now();
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
};

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("es-PY", { day: "2-digit", month: "short", year: "numeric" });
