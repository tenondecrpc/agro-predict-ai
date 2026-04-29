export const fmtPYG = (n: number) =>
  new Intl.NumberFormat("es-PY", { style: "currency", currency: "PYG", maximumFractionDigits: 0 }).format(n);

export const fmtNum = (n: number, digits = 0) =>
  new Intl.NumberFormat("es-PY", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(n);

export const fmtPct = (n: number, digits = 0) =>
  `${(n * 100).toFixed(digits)}%`;

export const fmtDate = (d: string | Date) => {
  const dt = typeof d === "string" ? new Date(d) : d;
  return new Intl.DateTimeFormat("es-PY", { day: "2-digit", month: "short", year: "numeric" }).format(dt);
};

export const daysUntil = (iso: string) => {
  const ms = new Date(iso).getTime() - Date.now();
  return Math.ceil(ms / (1000 * 60 * 60 * 24));
};
