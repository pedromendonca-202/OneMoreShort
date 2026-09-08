// Tiny DOM helpers. Every piece of dynamic data reaches the page through textContent, never innerHTML.
const SVG_NS = "http://www.w3.org/2000/svg";

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs && typeof attrs === "object" && !(attrs instanceof Node) && !Array.isArray(attrs)) {
    applyAttrs(el, attrs);
  } else if (attrs !== undefined && attrs !== null) {
    children.unshift(attrs);
  }
  append(el, children);
  return el;
}

function applyAttrs(el, attrs) {
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "style" && typeof value === "object") Object.assign(el.style, value);
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2).toLowerCase(), value);
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key === "value" || key === "checked" || key === "disabled" || key === "selected") el[key] = value;
    else el.setAttribute(key, value === true ? "" : String(value));
  }
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function svg(tag, attrs = {}, ...children) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2).toLowerCase(), value);
    else el.setAttribute(key, String(value));
  }
  append(el, children);
  return el;
}

export function icon(name, cls = "") {
  const el = svg("svg", { class: `ic ${cls}`.trim(), "aria-hidden": "true" });
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `/static/icons.svg#${name}`);
  el.append(use);
  return el;
}

export function text(value) {
  return document.createTextNode(String(value ?? ""));
}

export function on(el, event, handler, options) {
  el.addEventListener(event, handler, options);
  return () => el.removeEventListener(event, handler, options);
}
