// Core reusable components: Card, Pill, Button, IconCircle, Ring, MiniBars, Stepper, Thumb, Delta.
import { h, icon, svg, clear } from "../dom.js";

export function Card({ icon: iconName = null, iconColor = "red", title = "", subtitle = "", action = null, badge = null, body = [], cls = "", foot = null } = {}) {
  const head = title || action || badge
    ? h("div", { class: "card-head" },
        iconName ? icon(iconName, `card-icon ${iconColor}`) : null,
        h("div", { class: "card-titles" }, h("h2", { class: "card-title" }, title), subtitle ? h("p", { class: "card-sub" }, subtitle) : null),
        badge, action ? h("div", { class: "card-action-wrap" }, action) : null)
    : null;
  return h("section", { class: `card ${cls}`.trim() }, head, ...(Array.isArray(body) ? body : [body]), foot ? h("div", { class: "card-foot" }, foot) : null);
}

export function Pill(label, variant = "grey", { icon: iconName = null, size = "" } = {}) {
  return h("span", { class: `pill pill-${variant} ${size}`.trim() }, iconName ? icon(iconName) : null, label);
}

export function Button({ label = "", icon: iconName = null, variant = "primary", size = "", onClick = null, disabled = false, trailing = null, href = null, cls = "", title = null, type = "button" } = {}) {
  const inner = [iconName ? icon(iconName) : null, label ? h("span", {}, label) : null, trailing ? icon(trailing, "trail") : null];
  const attrs = { class: `btn btn-${variant} ${size} ${cls}`.trim(), disabled, title };
  if (href && !disabled) return h("a", { ...attrs, href, role: "button" }, ...inner);
  return h("button", { ...attrs, type, onClick }, ...inner);
}

export function LinkAction(label, { href = null, onClick = null, trailing = "chevron-right", icon: iconName = null } = {}) {
  const inner = [iconName ? icon(iconName) : null, label, trailing ? icon(trailing) : null];
  return href ? h("a", { class: "link-action", href }, ...inner) : h("button", { class: "link-action", type: "button", onClick }, ...inner);
}

export function IconCircle(name, color = "red", size = "") {
  return h("span", { class: `icon-circle ${color} ${size}`.trim() }, icon(name));
}

export function NumCircle(value, variant = "red") {
  return h("span", { class: `num-circle ${variant}` }, String(value));
}

export function CheckDot(kind = "green", size = "") {
  const names = { green: "check", red: "x", amber: "arrow-right", empty: null };
  const name = names[kind];
  return h("span", { class: `check-dot ${kind} ${size}`.trim() }, name ? icon(name) : null);
}

export function Ring(pct, { size = 44, color = "green", stroke = 4 } = {}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const value = pct === null || pct === undefined ? 0 : Math.max(0, Math.min(100, Number(pct)));
  const tone = pct === null || pct === undefined ? "grey" : color;
  const el = h("span", { class: `ring ${tone}`, style: { width: `${size}px`, height: `${size}px` } });
  el.append(svg("svg", { viewBox: `0 0 ${size} ${size}` },
    svg("circle", { class: "track", cx: size / 2, cy: size / 2, r, "stroke-width": stroke }),
    svg("circle", { class: "val", cx: size / 2, cy: size / 2, r, "stroke-width": stroke, "stroke-dasharray": `${c}`, "stroke-dashoffset": `${c * (1 - value / 100)}` })));
  return el;
}

export function MiniBars(series = [], count = 6) {
  const values = (series || []).slice(-count);
  while (values.length < count) values.unshift(0);
  const max = Math.max(1, ...values.map((v) => Number(v) || 0));
  return h("div", { class: "mini-bars" }, ...values.map((v, i) => h("span", { class: i >= values.length - 3 ? "on" : "", style: { height: `${Math.max(14, Math.round((Number(v) || 0) / max * 100))}%` } })));
}

export function Delta(value, unit = "%") {
  if (value === null || value === undefined) return h("span", { class: "delta flat" }, "—");
  const n = Number(value);
  const dir = n > 0 ? "up" : n < 0 ? "down" : "flat";
  const arrow = dir === "up" ? "arrow-up" : dir === "down" ? "arrow-down" : null;
  const label = unit === "%" ? `${n > 0 ? "+" : ""}${n}%` : `${n > 0 ? "+" : ""}${n} ${unit}`;
  return h("span", { class: `delta ${dir}` }, arrow ? icon(arrow, "ic-xs") : null, label);
}

export function DeltaPill(value, unit = "%") {
  const n = Number(value);
  const label = unit === "%" ? `${n > 0 ? "+" : ""}${n}%` : `${n > 0 ? "+" : ""}${n} ${unit}`;
  return h("span", { class: `delta-pill ${n < 0 ? "down" : ""}` }, icon(n < 0 ? "arrow-down" : "arrow-up"), label);
}

export function Thumb(url, { orientation = "v", cls = "", width = null, alt = "" } = {}) {
  const wrap = h("div", { class: `thumb ${orientation} ${cls}`.trim(), style: width ? { width: typeof width === "number" ? `${width}px` : width } : null });
  const fallback = h("div", { class: "thumb-fallback" }, LogoMark());
  wrap.append(fallback);
  if (url) {
    const img = h("img", { alt, loading: "lazy" });
    img.addEventListener("load", () => fallback.remove());
    img.addEventListener("error", () => img.remove());
    img.src = url;
    wrap.append(img);
  }
  return wrap;
}

export function LogoMark(size = 40) {
  return svg("svg", { class: "logo-mark", viewBox: "0 0 40 40", width: size, height: size, "aria-hidden": "true" },
    svg("rect", { x: 4, y: 4, width: 32, height: 32, rx: 9, fill: "#FF2233" }),
    svg("path", { d: "M16 13.5v13l11-6.5z", fill: "#fff" }));
}

export function Stepper(steps, { pendingLabel = "Pendente" } = {}) {
  const el = h("div", { class: "stepper" });
  steps.forEach((step, i) => {
    const num = step.status === "done" ? icon("check") : String(step.number);
    el.append(h("div", { class: `step ${step.status}` }, h("span", { class: "step-num" }, num),
      h("div", { class: "step-text" }, h("b", {}, step.name), h("span", {}, step.label || pendingLabel))));
    if (i < steps.length - 1) el.append(h("div", { class: `line ${step.status === "done" ? "done" : ""}` }));
  });
  return el;
}

export function setContent(el, ...children) {
  clear(el);
  el.append(...children.flat(Infinity).filter(Boolean));
  return el;
}
