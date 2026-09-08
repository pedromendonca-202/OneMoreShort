// Empty, loading, error and human-action states shared by every screen.
import { h, icon } from "../dom.js";
import { Button } from "./ui.js";

export function EmptyState({ icon: iconName = "circle-dashed", title = "Nada por aqui", text = "", action = null } = {}) {
  return h("div", { class: "empty" }, h("div", { class: "empty-icon" }, icon(iconName)), h("h3", {}, title), text ? h("p", {}, text) : null, action);
}

export function Skeleton({ height = 16, width = "100%", cls = "" } = {}) {
  return h("div", { class: `skeleton ${cls}`.trim(), style: { height: typeof height === "number" ? `${height}px` : height, width: typeof width === "number" ? `${width}px` : width } });
}

export function SkeletonCard(lines = 3, { height = 160 } = {}) {
  const items = [Skeleton({ height: 22, width: "40%" })];
  for (let i = 0; i < lines; i += 1) items.push(Skeleton({ height: 14, width: `${90 - i * 15}%` }));
  return h("section", { class: "card", style: { minHeight: `${height}px`, display: "flex", flexDirection: "column", gap: "14px" } }, ...items);
}

export function Progress(fraction = null) {
  const bar = h("div", { class: `progress ${fraction === null ? "indeterminate" : ""}` }, h("span", { style: { width: fraction === null ? "40%" : `${Math.round(fraction * 100)}%` } }));
  return bar;
}

export function HumanActionCard(report, { action = null, title = "Ação humana necessária" } = {}) {
  const rows = [
    ["Problema", report?.problem], ["Causa raiz", report?.root_cause], ["O que foi automatizado", report?.automated],
    ["O que falta", report?.remains], ["Ação humana necessária", report?.action], ["Próximo passo automático", report?.next_step],
  ];
  return h("div", { class: "human-action" },
    h("div", { class: "row" }, icon("triangle-alert", "red ic-lg"), h("h3", { class: "t-card" }, title)),
    h("dl", {}, ...rows.map(([k, v]) => [h("dt", {}, k), h("dd", {}, v || "—")])),
    action ? h("div", { style: { marginTop: "18px" } }, action) : null);
}

export function renderError(container, err) {
  container.append(EmptyState({ icon: "circle-alert", title: "Algo deu errado", text: err?.message || String(err),
    action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: () => location.reload() }) }));
}

export function NotFound() {
  return h("div", { class: "notfound" }, EmptyState({ icon: "compass", title: "Página não encontrada",
    text: "Essa rota não existe no painel. Volte para a tela Hoje.", action: Button({ label: "Ir para Hoje", icon: "house", href: "/" }) }));
}
