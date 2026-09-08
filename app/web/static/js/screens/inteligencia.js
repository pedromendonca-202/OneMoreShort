// Inteligência: what the channel learned from its own videos (highlights, patterns, themes, formats map, tests).
import { h, icon, svg } from "../dom.js";
import { api } from "../api.js";
import { router } from "../router.js";
import { sse } from "../sse.js";
import { fmtViews, capitalize } from "../format.js";
import { PageHeader } from "../components/header.js";
import { Card, Pill, Button, LinkAction, IconCircle, NumCircle, setContent } from "../components/ui.js";
import { EmptyState, Skeleton, SkeletonCard } from "../components/states.js";
import { toast, confirmDialog } from "../components/feedback.js";

const LIMITS = { patterns: 5, themes: 5, structures: 3, tests: 3 };
const SCATTER_COLORS = { ciencia: "#FF2233", curiosidades: "#B272F3", ilusoes: "#3B82F6", historia: "#F5AB14", tecnologia: "#3DF193" };
const SCATTER_FALLBACK = "#8A93A0";
const THEME_ICONS = {
  ciencia: ["flask-conical", "red"], curiosidades: ["lightbulb", "amber"], ilusoes: ["eye", "purple"],
  historia: ["book-open", "amber"], tecnologia: ["cpu", "blue"],
};
const STRUCTURE_ICONS = [["zap", "red"], ["circle-question-mark", "purple"], ["flask-conical", "blue"]];
const TEST_PILLS = ["red-solid", "purple", "blue"];
const LEGEND_ORDER = ["ciência", "curiosidades", "ilusões", "história", "tecnologia"];

export async function render(container) {
  container.append(PageHeader("Inteligência", "O que seu canal aprendeu com os dados dos seus vídeos."));
  const root = h("div", { class: "scr-inteligencia" });
  container.append(root);
  const expanded = { patterns: false, themes: false, structures: false, tests: false };
  let filter = "";
  let alive = true;

  setContent(root, skeleton());

  async function load() {
    let data;
    try {
      data = await api.get("/api/intelligence");
    } catch (err) {
      if (!alive) return;
      toast.error(err.message || "Não foi possível carregar a inteligência.");
      setContent(root, EmptyState({ icon: "circle-alert", title: "Algo deu errado", text: err.message || String(err),
        action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: load }) }));
      return;
    }
    if (!alive) return;
    if (!data.available || hasInsufficientSample(data)) { setContent(root, unavailable(data)); return; }
    draw(data);
  }

  function draw(data) {
    const ctx = { data, expanded, filter, redraw: () => draw(data), setFilter: (v) => { filter = v; draw(data); } };
    setContent(root,
      h("img", { class: "int-note", src: "/static/img/note-inteligencia.png", alt: "Dados transformam ideias em vídeos melhores", width: 111, height: 106 }),
      h("div", { class: "int-highlights" }, ...(data.highlights || []).map(Highlight)),
      h("div", { class: "int-cols" },
        h("div", { class: "int-col" }, PatternsCard(ctx), FormatsCard(ctx)),
        h("div", { class: "int-col" }, ThemesCard(ctx), StructuresCard(ctx), TestsCard(ctx))),
      Footer(data));
  }

  load();
  const offs = [
    sse.on("state", () => load()),
    sse.on("job", (job) => { if (job?.status === "done" && ["learn", "analytics"].includes(job.name)) load(); }),
  ];
  return () => { alive = false; offs.forEach((off) => off()); };
}

/* ---------- states ---------- */

function skeleton() {
  return h("div", { class: "int-skeleton" },
    h("div", { class: "int-highlights" }, ...[0, 1, 2, 3].map(() => SkeletonCard(2, { height: 156 }))),
    h("div", { class: "int-cols" },
      h("div", { class: "int-col" }, SkeletonCard(6, { height: 420 }), SkeletonCard(4, { height: 312 })),
      h("div", { class: "int-col" }, SkeletonCard(5, { height: 247 }), SkeletonCard(3, { height: 231 }), SkeletonCard(3, { height: 240 }))));
}

function unavailable(data) {
  const run = (path, okMessage) => async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    try {
      await api.post(path);
      toast.success(okMessage);
    } catch (err) {
      toast.error(err.message || "Falhou.");
    } finally {
      button.disabled = false;
    }
  };
  const detail = data.min_samples ? ` Amostra atual: ${data.sample || 0} de ${data.min_samples} vídeos medidos.` : "";
  return Card({ cls: "int-empty", body: EmptyState({ icon: "brain", title: "O canal ainda não aprendeu",
    text: `${data.reason || "Ainda não há dados suficientes."}${detail}`,
    action: h("div", { class: "row" },
      Button({ label: "Coletar analytics", icon: "refresh-cw", variant: "secondary", onClick: run("/api/analytics/collect", "Coleta de analytics iniciada.") }),
      Button({ label: "Aprender agora", icon: "brain", onClick: run("/api/learn", "Aprendizado iniciado.") })) }) });
}

/* ---------- highlights ---------- */

function Highlight(item) {
  const value = String(item.value ?? "—");
  const positive = value.startsWith("+") || (/^\d+([.,]\d+)?x$/.test(value) && parseFloat(value.replace(",", ".")) > 1);
  return h("section", { class: "card int-hl" },
    h("div", { class: "int-hl-top" }, circleIcon(item.icon, item.color || "grey", "lg"), h("h3", {}, item.title)),
    h("div", { class: "int-hl-value" }, h("b", { class: positive ? "green" : "" }, value), item.compare ? h("span", {}, item.compare) : null),
    h("p", { class: "int-hl-text" }, item.text),
    Pill(`base: ${item.n ?? 0} vídeos`, "dark", { size: "pill-sm int-hl-base" }));
}

/* ---------- patterns ---------- */

function PatternsCard(ctx) {
  const list = ctx.data.patterns || [];
  const rows = visible(list, "patterns", ctx.expanded);
  return Card({ icon: "search", title: "Padrões detectados", subtitle: "Insights baseados em dados reais do seu canal.", cls: "int-patterns",
    action: moreAction("Ver todos os padrões", "patterns", list, ctx),
    body: rows.length ? h("div", { class: "int-pattern-list" }, ...rows.map((p, i) => PatternRow(p, i)))
      : h("p", { class: "int-none" }, "Nenhum padrão com efeito positivo ainda.") });
}

function PatternRow(p, i) {
  const title = h("div", { class: "int-pattern-title" }, p.title, " ", h("span", { class: "green" }, p.gain), p.suffix ? ` ${p.suffix}` : "");
  return h("div", { class: "int-pattern" },
    NumCircle(i + 1, i === 0 ? "red" : "outline"),
    h("div", { class: "int-pattern-main" }, title,
      h("div", { class: "int-tags" }, ...(p.tags || []).map((t) => h("span", { class: "int-tag" }, t)))),
    Confidence(p.confidence),
    h("div", { class: "int-n" }, h("b", {}, String(p.n ?? 0)), h("span", {}, "vídeos")));
}

function Confidence(pct) {
  const value = Math.max(0, Math.min(100, Number(pct) || 0));
  return h("div", { class: "int-conf" }, h("span", { class: "int-conf-label" }, "Confiança"),
    h("div", { class: "int-conf-row" },
      h("div", { class: "int-bar", role: "meter", "aria-valuenow": value, "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": "Confiança" },
        h("span", { style: { width: `${value}%` } })),
      h("b", {}, `${value}%`)));
}

/* ---------- formats map (scatter) ---------- */

function FormatsCard(ctx) {
  const scatter = ctx.data.scatter || { points: [], categories: [], ideal: null };
  const select = h("select", { class: "int-filter-select", "aria-label": "Filtrar por tema", onChange: (e) => ctx.setFilter(e.target.value) },
    h("option", { value: "" }, "Todos os temas"),
    ...(scatter.categories || []).map((c) => h("option", { value: c, selected: c === ctx.filter }, capitalize(c))));
  const filterPill = h("span", { class: "int-filter pill pill-dark" }, select, icon("chevron-down", "ic-xs"));
  return Card({ icon: "target", title: "Mapa de formatos", subtitle: "Relação entre duração, retenção e visualizações dos seus vídeos.", cls: "int-formats",
    action: filterPill,
    body: h("div", { class: "int-scatter-wrap" }, Scatter(scatter, ctx.filter), Legend(scatter.categories || [])) });
}

function categoryKey(name) {
  return String(name || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function categoryColor(name) {
  return SCATTER_COLORS[categoryKey(name)] || SCATTER_FALLBACK;
}

function Scatter(scatter, filter) {
  const W = 436, H = 232, L = 58, R = 14, T = 26, B = 40;
  const pw = W - L - R, ph = H - T - B;
  const points = (scatter.points || []).filter((p) => Number.isFinite(Number(p.duration)));
  const maxDur = Math.max(60, ...points.map((p) => Number(p.duration) || 0), Number(scatter.ideal?.max) || 0);
  const xmax = Math.ceil(maxDur / 15) * 15;
  const x = (d) => L + (Number(d) / xmax) * pw;
  const y = (r) => T + (1 - Math.max(0, Math.min(100, Number(r))) / 100) * ph;
  const el = svg("svg", { class: "int-scatter", viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img", "aria-label": "Duração por retenção dos vídeos" });

  const grid = svg("g", { class: "grid" });
  for (let t = 0; t <= xmax; t += 15) grid.append(svg("line", { x1: x(t), x2: x(t), y1: T, y2: T + ph }));
  for (let t = 0; t <= 100; t += 25) grid.append(svg("line", { x1: L, x2: L + pw, y1: y(t), y2: y(t) }));
  el.append(grid);
  el.append(svg("line", { class: "axis", x1: L, x2: L, y1: T, y2: T + ph }), svg("line", { class: "axis", x1: L, x2: L + pw, y1: T + ph, y2: T + ph }));
  for (let t = 0; t <= xmax; t += 15) el.append(svg("text", { class: "tick", x: x(t), y: T + ph + 16, "text-anchor": "middle" }, String(t)));
  for (let t = 0; t <= 100; t += 25) el.append(svg("text", { class: "tick", x: L - 8, y: y(t) + 4, "text-anchor": "end" }, `${t}%`));
  el.append(svg("text", { class: "axis-title", x: L + pw / 2, y: H - 6, "text-anchor": "middle" }, "Duração do vídeo (segundos)"));
  el.append(svg("text", { class: "axis-title", x: 12, y: T + ph / 2, "text-anchor": "middle", transform: `rotate(-90 12 ${T + ph / 2})` }, "Retenção média"));

  const ideal = scatter.ideal;
  if (ideal && Number.isFinite(Number(ideal.min)) && Number.isFinite(Number(ideal.max))) {
    const inside = points.filter((p) => Number(p.duration) >= Number(ideal.min) && Number(p.duration) <= Number(ideal.max)).map((p) => Number(p.retention) || 0);
    let hi = inside.length ? Math.max(...inside) + 6 : 90, lo = inside.length ? Math.min(...inside) - 6 : 70;
    if (hi - lo < 18) { hi += (18 - (hi - lo)) / 2; lo = hi - 18; }
    hi = Math.min(100, hi); lo = Math.max(0, lo);
    const rx = x(ideal.min), rw = Math.max(6, x(ideal.max) - x(ideal.min));
    el.append(svg("rect", { class: "ideal", x: rx, y: y(hi), width: rw, height: Math.max(8, y(lo) - y(hi)), rx: 3 }));
    const label = String(ideal.label || "Zona ideal");
    const cut = label.indexOf(" (");
    const lines = cut > 0 ? [label.slice(0, cut), label.slice(cut + 1)] : [label];
    const cx = Math.max(L + 44, Math.min(L + pw - 44, rx + rw / 2));
    const top = Math.max(10, y(hi) - 6 - (lines.length - 1) * 12);
    lines.forEach((line, i) => el.append(svg("text", { class: "ideal-label", x: cx, y: top + i * 12, "text-anchor": "middle" }, line)));
  }

  const views = points.map((p) => Number(p.views) || 0);
  const vmin = Math.min(...views, Infinity), vmax = Math.max(...views, -Infinity);
  const radius = (v) => (vmax > vmin ? 5 + 8 * Math.sqrt((v - vmin) / (vmax - vmin)) : 8);
  const ordered = [...points].sort((a, b) => (Number(b.views) || 0) - (Number(a.views) || 0));
  const dots = svg("g", { class: "dots" });
  for (const p of ordered) {
    const dim = filter && p.category !== filter;
    const go = () => { if (p.id) router.navigate(`/desempenho/${encodeURIComponent(p.id)}`); };
    const label = `${p.title || p.id || "Vídeo"} — ${p.duration}s · ${p.retention}% · ${fmtViews(p.views)} views`;
    const dot = svg("circle", { class: `pt ${dim ? "dim" : ""}`.trim(), cx: x(p.duration), cy: y(p.retention), r: radius(Number(p.views) || 0),
      fill: categoryColor(p.category), tabindex: dim ? -1 : 0, role: "link", "aria-label": label,
      onClick: go, onKeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } } },
      svg("title", {}, label));
    dots.append(dot);
  }
  el.append(dots);
  return el;
}

function Legend(categories) {
  const ordered = [...categories].sort((a, b) => {
    const ai = LEGEND_ORDER.indexOf(String(a).toLowerCase());
    const bi = LEGEND_ORDER.indexOf(String(b).toLowerCase());
    return (ai < 0 ? LEGEND_ORDER.length : ai) - (bi < 0 ? LEGEND_ORDER.length : bi);
  }).slice(0, 5);
  return h("div", { class: "int-legend" }, h("span", { class: "int-legend-title" }, "Tamanho = Visualizações"),
    h("ul", {}, ...ordered.map((c) => h("li", {}, h("span", { class: "int-legend-dot", style: { background: categoryColor(c) } }), capitalize(c)))));
}

/* ---------- themes ---------- */

function ThemesCard(ctx) {
  const list = ctx.data.themes || [];
  const rows = visible(list, "themes", ctx.expanded);
  return Card({ icon: "chart-column", title: "Temas por performance", subtitle: "Comparativo de desempenho por tema no seu canal.", cls: "int-themes",
    action: moreAction("Ver todos os temas", "themes", list, ctx),
    body: h("div", { class: "int-table", role: "table" },
      h("div", { class: "int-th", role: "row" }, h("span", { role: "columnheader" }, "Tema"), h("span", { role: "columnheader" }, "Retenção média"), h("span", { role: "columnheader" }, "Inscritos / 1k views")),
      ...rows.map(ThemeRow),
      rows.length ? null : h("p", { class: "int-none" }, "Nenhum tema medido ainda.")) });
}

function ThemeRow(t) {
  const [name, color] = THEME_ICONS[categoryKey(t.category)] || ["tag", "grey"];
  const ret = Math.max(0, Math.min(100, Number(t.retention) || 0));
  return h("div", { class: "int-tr", role: "row" },
    h("div", { class: "int-td int-td-name", role: "cell" }, h("span", { class: `int-theme-icon ${color}` }, icon(name)), h("b", {}, capitalize(t.category))),
    h("div", { class: "int-td int-td-ret", role: "cell" }, h("div", { class: "int-bar" }, h("span", { style: { width: `${ret}%` } })), h("span", {}, `${ret}%`)),
    h("div", { class: "int-td int-td-subs", role: "cell" }, h("span", { class: "int-dot-green" }), h("span", {}, Number(t.subs_per_1k || 0).toFixed(1).replace(".", ","))));
}

/* ---------- structures ---------- */

function StructuresCard(ctx) {
  const list = ctx.data.structures || [];
  const rows = visible(list, "structures", ctx.expanded);
  return Card({ icon: "clapperboard", title: "Estruturas narrativas", subtitle: "Formatos que mais funcionam no seu canal.", cls: "int-structures",
    action: moreAction("Ver todas as estruturas", "structures", list, ctx),
    body: rows.length ? h("div", { class: "int-struct-grid" }, ...rows.map((s, i) => {
      const [name, color] = STRUCTURE_ICONS[i % STRUCTURE_ICONS.length];
      const negative = String(s.result || "").trim().startsWith("-");
      return h("div", { class: "int-struct" }, IconCircle(name, color), h("b", {}, s.name), h("p", {}, s.description),
        Pill(s.result || "—", negative ? "red" : "green-soft", { size: "pill-sm" }));
    })) : h("p", { class: "int-none" }, "Nenhuma estrutura observada ainda.") });
}

/* ---------- tests ---------- */

function TestsCard(ctx) {
  const list = ctx.data.tests || [];
  const rows = visible(list, "tests", ctx.expanded);
  return Card({ icon: "flask-conical", title: "Próximos testes recomendados", subtitle: "Experimentos baseados nos insights do seu canal.", cls: "int-tests",
    action: moreAction("Ver todos os testes", "tests", list, ctx),
    body: rows.length ? h("div", { class: "int-test-grid" }, ...rows.map((t, i) => TestCard(t, i))) : h("p", { class: "int-none" }, "Nenhum teste recomendado ainda.") });
}

function TestCard(t, i) {
  const number = t.number ?? i + 1;
  const conf = Math.max(0, Math.min(100, Number(t.confidence) || 0));
  return h("div", { class: "int-test" },
    Pill(`Teste ${number}`, TEST_PILLS[(number - 1) % TEST_PILLS.length], { size: "pill-sm" }),
    h("b", { class: "int-test-title" }, t.title),
    h("p", { class: "int-test-hyp" }, h("span", {}, "Hipótese: "), t.hypothesis),
    h("div", { class: "int-test-line" }, h("span", {}, "Impacto esperado"), h("b", { class: "green" }, t.impact || "—")),
    h("div", { class: "int-test-line" }, h("span", {}, "Confiança"), h("div", { class: "int-bar" }, h("span", { style: { width: `${conf}%` } })), h("b", {}, `${conf}%`)),
    Button({ label: "Adicionar ao Estúdio", icon: "rocket", size: "btn-sm btn-block", onClick: () => addTest(t, number) }));
}

async function addTest(test, number) {
  const ok = await confirmDialog({ title: "Adicionar este teste?", body: "Uma nova produção será aberta para você aplicar esta hipótese.", confirmLabel: "Adicionar", icon: "rocket" });
  if (!ok) return;
  try {
    const result = await api.post("/api/productions", { force: false });
    toast.success(`Teste ${number} adicionado`);
    if (result?.id) router.navigate(`/estudio/${encodeURIComponent(result.id)}`);
  } catch (err) {
    toast.error(err.status === 409 ? err.message : (err.message || "Não foi possível criar a produção."));
  }
}

/* ---------- footer ---------- */

function Footer(data) {
  return h("div", { class: "int-foot" },
    h("div", { class: "int-foot-left" }, h("span", { class: "int-foot-icon" }, icon("info")), h("span", {}, "Todas as recomendações mostram peso estatístico e diferença vs média do canal.")),
    h("span", { class: "int-foot-right" }, `Dados atualizados em ${data.updated_label || "—"}.`));
}

/* ---------- helpers ---------- */

function visible(list, key, expanded) {
  const items = Array.isArray(list) ? list : [];
  return expanded[key] ? items : items.slice(0, LIMITS[key]);
}

function moreAction(label, key, list, ctx) {
  const hasMore = Array.isArray(list) && list.length > LIMITS[key];
  const open = ctx.expanded[key];
  const btn = LinkAction(open ? "Ver menos" : label, { onClick: () => {
    if (!hasMore && !open) { toast.info("Tudo já está visível: a lista completa cabe nesta tela."); return; }
    ctx.expanded[key] = !open;
    ctx.redraw();
  } });
  if (hasMore) btn.setAttribute("aria-expanded", open ? "true" : "false");
  return btn;
}

function hasInsufficientSample(data) {
  const sample = Number(data?.sample);
  const minimum = Number(data?.min_samples);
  return Number.isFinite(sample) && Number.isFinite(minimum) && minimum > 0 && sample < minimum;
}

function circleIcon(name, color, size = "") {
  if (name === "magnet") return h("span", { class: `icon-circle ${color} ${size}`.trim() }, magnetIcon());
  return IconCircle(name, color, size);
}

// Lucide "magnet" is missing from icons.svg; drawn inline.
function magnetIcon() {
  return svg("svg", { class: "ic", viewBox: "0 0 24 24", "aria-hidden": "true" },
    svg("path", { d: "m6 15-4-4 6.75-6.77a7.79 7.79 0 0 1 11 11L13 22l-4-4 6.39-6.36a2.14 2.14 0 0 0-3-3L6 15" }),
    svg("path", { d: "m5 8 4 4" }), svg("path", { d: "m12 15 4 4" }));
}
