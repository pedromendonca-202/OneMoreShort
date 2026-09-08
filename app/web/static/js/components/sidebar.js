// Fixed sidebar: 3D logo, tagline, seven nav items, system + spend cards, footer with the hand-drawn stroke.
import { h, icon, svg } from "../dom.js";
import { state } from "../state.js";
import { fmtMoneyBRL } from "../format.js";
import { router } from "../router.js";

export const NAV = [
  { path: "/", icon: "house", label: "Hoje", match: (p) => p === "/" },
  { path: "/estudio", icon: "clapperboard", label: "Estúdio", match: (p) => p.startsWith("/estudio") },
  { path: "/conversa", icon: "message-circle", label: "Conversa", match: (p) => p.startsWith("/conversa") },
  { path: "/biblioteca", icon: "folder", label: "Biblioteca", match: (p) => p.startsWith("/biblioteca") },
  { path: "/desempenho", icon: "chart-column-big", label: "Desempenho", match: (p) => p.startsWith("/desempenho") },
  { path: "/inteligencia", icon: "brain", label: "Inteligência", match: (p) => p.startsWith("/inteligencia") },
  { path: "/ajustes", icon: "settings", label: "Ajustes", match: (p) => p.startsWith("/ajustes") },
];

const STATUS_CLASS = { ready: "green", busy: "amber", warn: "amber", error: "red" };

export function renderSidebar(container) {
  const items = NAV.map((item) => h("a", { class: "sb-item", href: item.path, dataset: { path: item.path } }, icon(item.icon), h("span", {}, item.label)));
  const dot = h("span", { class: "dot green" });
  const statusValue = h("span", { class: "sb-card-value green" }, "Pronto");
  const spendValue = h("span", { class: "sb-card-value" }, "R$ 0,00");

  container.append(
    h("img", { class: "sb-logo", src: "/static/img/logo-3d.png", alt: "OneMoreShort" }),
    h("p", { class: "sb-tagline" }, "Ideias hoje,", h("br"), "vídeos sempre."),
    h("nav", { class: "sb-nav", "aria-label": "Seções" }, ...items),
    h("div", { class: "sb-spacer" }),
    h("a", { class: "sb-card", href: "/ajustes", title: "Saúde do sistema" }, dot,
      h("div", { class: "grow" }, h("span", { class: "sb-card-label" }, "Sistema"), statusValue), icon("chevron-right", "chev")),
    h("a", { class: "sb-card", href: "/ajustes", title: "Custos" }, h("span", { class: "sb-wallet" }, icon("wallet")),
      h("div", { class: "grow" }, h("span", { class: "sb-card-label" }, "Gasto hoje"), spendValue), icon("chevron-right", "chev")),
    h("p", { class: "sb-foot" }, "Mais ideias.", h("br"), "Mais conteúdo.", h("br"), "Um mundo mais curioso.",
      svg("svg", { viewBox: "0 0 46 8", "aria-hidden": "true" }, svg("path", { d: "M1 5.5 C 10 2.5, 20 1.5, 30 3 S 42 5.5, 45 3.2", stroke: "#FF2233", "stroke-width": "2.2", fill: "none", "stroke-linecap": "round" }))),
  );

  const setActive = ({ path }) => {
    items.forEach((el, i) => { if (NAV[i].match(path)) el.setAttribute("aria-current", "page"); else el.removeAttribute("aria-current"); });
  };
  router.onChange(setActive);
  setActive(router.current);

  state.subscribe((s) => {
    dot.className = `dot ${STATUS_CLASS[s.system.status] || "green"}`;
    statusValue.className = `sb-card-value ${STATUS_CLASS[s.system.status] || "green"}`;
    statusValue.textContent = s.system.label;
    spendValue.textContent = fmtMoneyBRL(s.system.spendUsd);
  });
}
