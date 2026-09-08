// Number, date and text formatting in Brazilian Portuguese.
const MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const WEEKDAYS = ["Domingo", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"];

export function fmtViews(value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")} mi`;
  if (n >= 1000) return `${Math.round(n / 1000)} mil`;
  return String(n);
}

export function fmtInt(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("pt-BR");
}

export function fmtMoneyBRL(usd) {
  const value = Number(usd || 0) * 5.0; // display only; the ledger is kept in USD
  return `R$ ${value.toFixed(2).replace(".", ",")}`;
}

export function fmtPct(value, digits = 0) {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(digits).replace(".", ",")}%`;
}

export function fmtDelta(value, unit = "%") {
  if (value === null || value === undefined) return null;
  const n = Number(value);
  const sign = n > 0 ? "+" : n < 0 ? "−" : "";
  return `${sign}${Math.abs(n)}${unit === "%" ? "%" : ` ${unit}`}`;
}

export function fmtDateLong(date) {
  const d = date instanceof Date ? date : new Date(date);
  return `${d.getDate()} de ${MONTHS[d.getMonth()]} de ${d.getFullYear()}`;
}

export function weekday(date) {
  const d = date instanceof Date ? date : new Date(date);
  return WEEKDAYS[d.getDay()];
}

export function fmtClock(seconds) {
  if (seconds === null || seconds === undefined) return "--:--";
  const total = Math.round(seconds);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

export function fmtSeconds(seconds, digits = 1) {
  if (seconds === null || seconds === undefined) return "—";
  return `${Number(seconds).toFixed(digits).replace(".", ",")}s`;
}

export function fmtBytes(bytes) {
  if (bytes === null || bytes === undefined) return "—";
  if (bytes >= 1024 * 1024) return `${Math.round(bytes / 1024 / 1024)} MB`;
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${bytes} B`;
}

export function fmtElapsed(seconds) {
  const s = Math.max(0, Math.round(seconds || 0));
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}min ${String(s % 60).padStart(2, "0")}s`;
}

export function capitalize(value) {
  const s = String(value || "");
  return s.charAt(0).toUpperCase() + s.slice(1);
}
