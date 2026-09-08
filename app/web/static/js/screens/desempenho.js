// Desempenho: per-video analytics (KPIs, retention curve with annotations, script timeline, learnings, comparison).
import { h, icon, svg } from "../dom.js";
import { api } from "../api.js";
import { sse } from "../sse.js";
import { fmtInt } from "../format.js";
import { PageHeader } from "../components/header.js";
import { Card, Button, IconCircle, CheckDot, Ring, Thumb, DeltaPill, setContent } from "../components/ui.js";
import { EmptyState, Skeleton } from "../components/states.js";
import { toast } from "../components/feedback.js";

const RED = "#FF2233";

export async function render(container, params) {
  container.append(PageHeader("Desempenho", "Acompanhe o desempenho dos seus vídeos e entenda o que gera mais engajamento."));
  const root = h("div", { class: "scr-desempenho" });
  container.append(root);
  setContent(root, skeleton());

  let alive = true;
  let id = params?.id || null;

  const load = async ({ quiet = false } = {}) => {
    try {
      if (!id) {
        const latest = await api.get("/api/analytics/latest");
        id = latest?.id || null;
        if (!id) {
          if (alive) setContent(root, emptyNoVideo());
          return;
        }
      }
      const data = await api.get(`/api/analytics/${encodeURIComponent(id)}`);
      if (!alive) return;
      if (!data?.available) setContent(root, emptyUnavailable(data, load));
      else setContent(root, screen(data));
    } catch (err) {
      if (!alive) return;
      if (!quiet) toast.error(err?.message || "Não foi possível carregar o desempenho.");
      setContent(root, EmptyState({ icon: "circle-alert", title: "Não foi possível carregar o desempenho", text: err?.message || "",
        action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: () => { setContent(root, skeleton()); load(); } }) }));
    }
  };

  await load();
  const offs = [sse.on("snapshot", () => load({ quiet: true })), sse.on("state", () => load({ quiet: true }))];
  return () => { alive = false; offs.forEach((off) => off()); };
}

// ----------------------------------------------------------------------------- states

function emptyNoVideo() {
  return h("section", { class: "card dp-empty" }, EmptyState({ icon: "chart-column", title: "Nenhum vídeo publicado ainda",
    text: "Publique um vídeo para acompanhar views, retenção, curtidas e inscritos aqui.",
    action: Button({ label: "Ir para a Biblioteca", icon: "folder", href: "/biblioteca" }) }));
}

function emptyUnavailable(data, reload) {
  const collect = Button({ label: "Coletar analytics", icon: "refresh-cw", onClick: async () => {
    collect.disabled = true;
    try {
      await api.post("/api/analytics/collect");
      toast.success("Coleta de analytics iniciada.");
      reload({ quiet: true });
    } catch (err) {
      toast.error(err?.message || "Não foi possível coletar analytics.");
    } finally { collect.disabled = false; }
  } });
  return h("section", { class: "card dp-empty" }, EmptyState({ icon: "chart-column", title: data?.title || "Sem analytics ainda",
    text: data?.reason || "Sem analytics ainda.", action: h("div", { class: "dp-empty-actions" }, collect,
      data?.id ? Button({ label: "Voltar à biblioteca", icon: "chevron-left", variant: "secondary", href: `/biblioteca/${encodeURIComponent(data.id)}` }) : null) }));
}

function skeleton() {
  const kpi = () => h("section", { class: "card dp-kpi" }, Skeleton({ height: 56, width: 56, cls: "dp-sk-circle" }),
    h("div", { class: "dp-kpi-body" }, Skeleton({ height: 14, width: "40%" }), Skeleton({ height: 30, width: "60%" }), Skeleton({ height: 26, width: "45%" }), Skeleton({ height: 12, width: "80%" })));
  const list = () => h("section", { class: "card" }, Skeleton({ height: 18, width: "60%" }), h("div", { class: "dp-sk-stack" },
    Skeleton({ height: 14, width: "85%" }), Skeleton({ height: 12, width: "70%" }), Skeleton({ height: 14, width: "80%" }), Skeleton({ height: 12, width: "65%" }), Skeleton({ height: 14, width: "75%" })));
  return [
    h("section", { class: "card dp-top" }, Skeleton({ height: 96, width: 190 }), h("div", { class: "dp-top-text" }, Skeleton({ height: 14, width: 170 }), Skeleton({ height: 34, width: 460 }), Skeleton({ height: 14, width: 150 })),
      h("div", { class: "dp-top-actions" }, Skeleton({ height: 52, width: 210 }), Skeleton({ height: 52, width: 204 }))),
    h("div", { class: "dp-kpis" }, kpi(), kpi(), kpi(), kpi()),
    h("div", { class: "dp-mid" }, h("section", { class: "card" }, Skeleton({ height: 22, width: "30%" }), Skeleton({ height: 14, width: "55%", cls: "dp-sk-gap" }), Skeleton({ height: 200 })), list()),
    h("div", { class: "dp-bottom" }, list(), list(), list(), h("section", { class: "card" }, Skeleton({ height: 18, width: "70%" }), Skeleton({ height: 120, cls: "dp-sk-gap" }), Skeleton({ height: 54 }))),
  ];
}

// ----------------------------------------------------------------------------- screen

function screen(data) {
  return [topBand(data), kpiRow(data.kpis || []),
    h("div", { class: "dp-mid" }, curveCard(data.curve || {}, data.duration_s), scriptCard(data.script_timeline || [])),
    h("div", { class: "dp-bottom" },
      listCard("O que funcionou", h("span", { class: "dp-head-badge green" }, icon("check")), data.worked, "green"),
      listCard("O que falhou", h("span", { class: "dp-head-badge red" }, icon("x")), data.failed, "red"),
      listCard("Recomendação para o próximo", icon("lightbulb", "dp-head-icon amber"), data.recommendation, "amber"),
      comparisonCard(data.comparison || {}, data.duration_s))];
}

function topBand(data) {
  const thumb = Thumb(data.thumb_url, { orientation: "h", width: 190, alt: data.title || "" });
  const image = thumb.querySelector("img");
  if (image) image.loading = "eager";
  thumb.classList.add("dp-thumb");
  thumb.append(h("span", { class: "dp-thumb-dur" }, shortDuration(data.duration, data.duration_s)));
  return h("section", { class: "card dp-top" }, thumb,
    h("div", { class: "dp-top-text" },
      h("p", { class: "dp-top-when" }, data.published_label || ""),
      h("h2", { class: "dp-top-title ellipsis", title: data.title || "" }, data.title || ""),
      h("p", { class: "dp-top-id" }, data.id || "")),
    h("div", { class: "dp-top-actions" },
      Button({ label: "Voltar à biblioteca", icon: "chevron-left", variant: "secondary", cls: "dp-btn", href: `/biblioteca/${encodeURIComponent(data.id || "")}` }),
      Button({ label: "Exportar relatório", icon: "download", variant: "danger", cls: "dp-btn dp-btn-export", onClick: () => exportReport(data) })));
}

function exportReport(data) {
  const isMd = typeof data.report_markdown === "string" && data.report_markdown.trim().length > 0;
  const body = isMd ? data.report_markdown : "```json\n" + JSON.stringify(data, null, 2) + "\n```\n";
  const blob = new Blob([body], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const id = String(data.id || "video").replace(/[^a-zA-Z0-9._-]+/g, "-").slice(0, 80) || "video";
  const a = h("a", { href: url, download: `relatorio-${id}.md`, style: { display: "none" } });
  document.body.append(a);
  a.click();
  setTimeout(() => { a.remove(); URL.revokeObjectURL(url); }, 1000);
  toast.success("Relatório exportado.");
}

function shortDuration(label, seconds) {
  const s = seconds === null || seconds === undefined || !Number.isFinite(Number(seconds)) ? null : Math.round(Number(seconds));
  if (s !== null) return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  return String(label || "").replace(/^0(\d):/, "$1:");
}

// ----------------------------------------------------------------------------- KPIs

const KPI_ICONS = { views: "eye", retention: null, likes: "heart", subscribers: "user" };

function kpiRow(kpis) {
  return h("div", { class: "dp-kpis" }, ...kpis.map(kpiCard));
}

function kpiCard(k) {
  const value = k.format === "pct" ? `${fmtNum(k.value)}%` : fmtInt(k.value);
  let circle;
  if (k.key === "retention") {
    circle = h("span", { class: "icon-circle dp-kpi-icon" }, Ring(k.value, { size: 28, color: "green", stroke: 4 }));
  } else {
    circle = IconCircle(KPI_ICONS[k.key] || "activity", "red", "lg");
    circle.classList.add("dp-kpi-icon");
  }
  const delta = k.delta === null || k.delta === undefined ? null : DeltaPill(k.delta, k.delta_unit || "%");
  const share = k.share ? h("span", { class: "dp-kpi-share" }, h("b", {}, k.share), " da audiência") : null;
  return h("section", { class: "card dp-kpi" }, circle,
    h("div", { class: "dp-kpi-body" },
      h("span", { class: "dp-kpi-label" }, k.label || ""),
      h("span", { class: "dp-kpi-value" }, value),
      h("div", { class: "dp-kpi-delta" }, share, delta),
      h("span", { class: "dp-kpi-compare" }, normalizeCompare(k.compare))));
}

function fmtNum(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(1).replace(".", ",");
}

function normalizeCompare(text) {
  return String(text || "").replace(/^vs,\s*/i, "vs. ");
}

// ----------------------------------------------------------------------------- retention curve

const CURVE = { w: 766, h: 228, left: 40, right: 760, top: 12, bottom: 198, labelY: 220 };

function curveCard(curve, durationS) {
  const duration = Number(curve.duration_s || durationS || 0) || 0;
  const points = (curve.points || []).map((p) => ({ t: Number(p.t), value: Number(p.value) })).filter((p) => Number.isFinite(p.t) && Number.isFinite(p.value));
  const annotations = curve.annotations || [];
  const body = points.length
    ? curveChart(points, annotations, duration)
    : h("p", { class: "dp-none" }, "A curva de retenção ainda não chegou.");
  return Card({ icon: "chart-column", title: "Curva de retenção", subtitle: "Veja em que momentos os espectadores mais abandonam o vídeo.",
    cls: "dp-curve-card", action: filterPill("Todos os espectadores"), body });
}

function filterPill(label) {
  // Pill() from ui.js only takes a leading icon; the reference shows a trailing chevron.
  return h("span", { class: "pill pill-dark dp-pill-filter" }, label, icon("chevron-down"));
}

function curveChart(points, annotations, duration) {
  const C = CURVE;
  const maxT = Math.max(40, Math.ceil(duration));
  const sx = (t) => C.left + (t / maxT) * (C.right - C.left);
  const sy = (v) => C.top + ((100 - Math.max(0, Math.min(100, v))) / 100) * (C.bottom - C.top);
  const line = points.map((p, i) => `${i ? "L" : "M"}${sx(p.t).toFixed(1)},${sy(p.value).toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  const first = points[0];
  const area = `${line} L${sx(last.t).toFixed(1)},${C.bottom} L${sx(first.t).toFixed(1)},${C.bottom} Z`;

  const defs = svg("defs", {},
    svg("linearGradient", { id: "dp-area", x1: 0, y1: 0, x2: 0, y2: 1 },
      svg("stop", { offset: "0%", "stop-color": RED, "stop-opacity": .55 }),
      svg("stop", { offset: "55%", "stop-color": RED, "stop-opacity": .22 }),
      svg("stop", { offset: "100%", "stop-color": RED, "stop-opacity": 0 })),
    svg("filter", { id: "dp-glow", x: "-10%", y: "-30%", width: "120%", height: "160%" },
      svg("feGaussianBlur", { stdDeviation: 3 })));

  const grid = [0, 25, 50, 75, 100].map((v) => svg("line", { x1: C.left, x2: C.right, y1: sy(v), y2: sy(v), class: "dp-grid" }));
  const yLabels = [0, 25, 50, 75, 100].map((v) => svg("text", { x: C.left - 10, y: sy(v) + 4, class: "dp-axis", "text-anchor": "end" }, `${v}%`));

  const ticks = [];
  for (let t = 0; t <= maxT; t += 5) ticks.push(t);
  const dur = Math.round(duration);
  if (dur > 0 && !ticks.includes(dur)) {
    const filtered = ticks.filter((t) => Math.abs(t - dur) > 2);
    filtered.push(dur);
    ticks.length = 0;
    ticks.push(...filtered.sort((a, b) => a - b));
  }
  const xLabels = ticks.map((t) => svg("text", { x: sx(t), y: C.labelY, class: `dp-axis ${t === dur ? "dur" : ""}`, "text-anchor": "middle" }, `${t}s`));

  const marks = annotations.map((a) => {
    const x = sx(Number(a.t)), y = sy(Number(a.value));
    return [
      svg("line", { x1: x, x2: x, y1: C.top, y2: C.bottom, class: "dp-vline" }),
      svg("circle", { cx: x, cy: y, r: 5.5, class: "dp-point" }),
    ];
  });

  const chart = svg("svg", { viewBox: `0 0 ${C.w} ${C.h}`, class: "dp-svg", role: "img", "aria-label": "Curva de retenção" },
    defs, ...grid, ...yLabels, ...xLabels,
    svg("path", { d: area, fill: "url(#dp-area)" }),
    svg("path", { d: line, class: "dp-line-glow", filter: "url(#dp-glow)" }),
    svg("path", { d: line, class: "dp-line" }),
    ...marks.flat());

  const notes = annotations.map((a) => annotationBalloon(a, sx(Number(a.t)) / C.w * 100, sy(Number(a.value)) / C.h * 100, Number(a.value)));
  return h("div", { class: "dp-chart" }, chart, ...notes);
}

function annotationBalloon(a, xPct, yPct, value) {
  const major = a.kind === "major";
  const el = h("div", { class: `dp-note ${major ? "major" : "small"}` });
  if (major) {
    el.append(h("b", {}, a.label || ""), a.sub ? h("span", {}, a.sub) : null, a.sentence ? h("span", { class: "dp-note-quote" }, `“${a.sentence}”`) : null);
  } else {
    el.append(h("b", {}, a.label || ""), a.sub ? h("span", {}, a.sub) : null, a.note ? h("span", {}, a.note) : null);
  }
  const anchorRight = xPct > 88;
  if (anchorRight) el.style.right = `calc(${(100 - xPct).toFixed(2)}% + 10px)`;
  else el.style.left = `calc(${xPct.toFixed(2)}% + ${major ? 12 : 8}px)`;
  // The major balloon hangs from the top of the plot (as in the reference); small ones sit just above their point,
  // or beside it when the point is already near the top.
  if (major) el.style.top = "0px";
  else if (value >= 80) el.style.top = `calc(${yPct.toFixed(2)}% - 14px)`;
  else el.style.bottom = `calc(${(100 - yPct).toFixed(2)}% + 10px)`;
  return el;
}

// ----------------------------------------------------------------------------- script timeline

function scriptCard(scenes) {
  const list = scenes.length
    ? h("ol", { class: "dp-scenes" }, ...scenes.map((s) => h("li", { class: `dp-scene ${s.highlight ? "hl" : ""}` },
        h("span", { class: "dp-scene-range t-mono" }, s.range || ""),
        h("span", { class: "dp-scene-dot" }),
        h("div", { class: "dp-scene-text" }, h("b", {}, s.title || `Cena ${s.index || ""}`), h("span", {}, s.text || "")))))
    : h("p", { class: "dp-none" }, "Nada detectado ainda.");
  return Card({ icon: "file-text", title: "Roteiro do vídeo", cls: "dp-script-card", body: list });
}

// ----------------------------------------------------------------------------- learnings

function listCard(title, headIcon, items, tone) {
  const list = (items || []).length
    ? h("ul", { class: `dp-items tone-${tone}` }, ...items.map((it) => h("li", { class: "dp-item" }, CheckDot(tone),
        h("div", { class: "dp-item-text" }, h("b", {}, it.title || ""), it.text ? h("span", {}, it.text) : null))))
    : h("p", { class: "dp-none" }, "Nada detectado ainda.");
  return h("section", { class: "card dp-list-card" }, h("div", { class: "dp-list-head" }, headIcon, h("h2", { class: "dp-list-title" }, title)), list);
}

// ----------------------------------------------------------------------------- comparison

const CMP = { w: 330, h: 130, left: 34, right: 300, top: 8, bottom: 106, labelY: 125 };

function comparisonCard(cmp, durationS) {
  const xs = (cmp.xs || []).map(Number);
  const video = (cmp.video || []).map(Number);
  const channel = (cmp.channel || []).map(Number);
  const has = xs.length > 1 && video.length === xs.length;
  const gainNum = cmp.gain === null || cmp.gain === undefined ? null : Number(cmp.gain);
  const gainBlock = h("div", { class: "dp-gain" }, icon("trophy", "dp-gain-icon"),
    h("div", {},
      gainNum === null
        ? h("b", {}, "Sem base de comparação ainda")
        : h("b", {}, h("span", { class: "dp-gain-num" }, `${gainNum > 0 ? "+" : ""}${fmtNum(gainNum)}%`), " de retenção"),
      h("span", {}, gainNum === null ? "Publique mais vídeos para comparar com a média do canal." : "em relação à média do canal no final do vídeo.")));
  const legend = h("div", { class: "dp-legend" },
    h("span", {}, h("i", { class: "dp-legend-dot red" }), "Este vídeo"),
    h("span", {}, h("i", { class: "dp-legend-dot grey" }), "Média do canal"));
  const chart = has ? comparisonChart(xs, video, channel, cmp, durationS) : h("p", { class: "dp-none" }, "Nada detectado ainda.");
  return h("section", { class: "card dp-cmp-card" },
    h("div", { class: "dp-list-head" }, icon("chart-column", "dp-head-icon red"), h("h2", { class: "dp-list-title" }, "Comparativo de retenção"),
      filterPill("Este vídeo vs. média")),
    legend, chart, gainBlock);
}

function comparisonChart(xs, video, channel, cmp, durationS) {
  const C = CMP;
  const maxT = Math.max(40, Math.ceil(xs[xs.length - 1] || 0), Math.ceil(Number(durationS) || 0));
  const sx = (t) => C.left + (t / maxT) * (C.right - C.left);
  const sy = (v) => C.top + ((100 - Math.max(0, Math.min(100, v))) / 100) * (C.bottom - C.top);
  const path = (ys) => xs.map((t, i) => `${i ? "L" : "M"}${sx(t).toFixed(1)},${sy(ys[i]).toFixed(1)}`).join(" ");
  const vLine = path(video);
  const vArea = `${vLine} L${sx(xs[xs.length - 1]).toFixed(1)},${C.bottom} L${sx(xs[0]).toFixed(1)},${C.bottom} Z`;
  const hasChannel = channel.length === xs.length;
  const grid = [0, 25, 50, 75, 100].map((v) => svg("line", { x1: C.left, x2: C.right, y1: sy(v), y2: sy(v), class: "dp-grid" }));
  const yLabels = [0, 25, 50, 75, 100].map((v) => svg("text", { x: C.left - 8, y: sy(v) + 3.5, class: "dp-axis xs", "text-anchor": "end" }, `${v}%`));
  const xLabels = [];
  for (let t = 0; t <= maxT; t += 10) xLabels.push(svg("text", { x: sx(t), y: C.labelY, class: "dp-axis xs", "text-anchor": "middle" }, `${t}s`));
  const endT = xs[xs.length - 1];
  const vEnd = cmp.video_end ?? video[video.length - 1];
  const cEnd = cmp.channel_end ?? (hasChannel ? channel[channel.length - 1] : null);
  const endLabels = [svg("text", { x: sx(endT) + 8, y: sy(vEnd) + 4, class: "dp-end red" }, `${fmtNum(vEnd)}%`)];
  if (cEnd !== null && cEnd !== undefined) {
    let cy = sy(cEnd) + 4;
    if (Math.abs(cy - (sy(vEnd) + 4)) < 12) cy = sy(vEnd) + 4 + 13;
    endLabels.push(svg("text", { x: sx(endT) + 8, y: cy, class: "dp-end grey" }, `${fmtNum(cEnd)}%`));
  }
  return svg("svg", { viewBox: `0 0 ${C.w} ${C.h}`, class: "dp-svg dp-cmp-svg", role: "img", "aria-label": "Comparativo de retenção" },
    svg("defs", {}, svg("linearGradient", { id: "dp-cmp-area", x1: 0, y1: 0, x2: 0, y2: 1 },
      svg("stop", { offset: "0%", "stop-color": RED, "stop-opacity": .45 }), svg("stop", { offset: "100%", "stop-color": RED, "stop-opacity": 0 }))),
    ...grid, ...yLabels, ...xLabels,
    svg("path", { d: vArea, fill: "url(#dp-cmp-area)" }),
    hasChannel ? svg("path", { d: path(channel), class: "dp-line-grey" }) : null,
    svg("path", { d: vLine, class: "dp-line thin" }),
    svg("circle", { cx: sx(endT), cy: sy(vEnd), r: 4.5, class: "dp-point" }),
    hasChannel ? svg("circle", { cx: sx(endT), cy: sy(cEnd), r: 4.5, class: "dp-point grey" }) : null,
    ...endLabels);
}
