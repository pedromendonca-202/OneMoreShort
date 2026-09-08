// Screen "Hoje" (route /): hero banner with the next action, stepper, chosen theme, production timeline,
// last published videos and the channel summary. Data comes from GET /api/today and is refreshed on SSE.
import { h, icon, svg } from "../dom.js";
import { api } from "../api.js";
import { sse } from "../sse.js";
import { fmtViews, fmtInt, fmtPct, fmtElapsed } from "../format.js";
import { PageHeader } from "../components/header.js";
import { Card, Pill, Button, LinkAction, CheckDot, Ring, Thumb, Stepper, setContent } from "../components/ui.js";
import { EmptyState, Skeleton, SkeletonCard, Progress, HumanActionCard } from "../components/states.js";
import { toast, confirmDialog, copyText } from "../components/feedback.js";

const REFRESH_DEBOUNCE_MS = 300;
const THEME_REFERENCE_THUMB = "/static/img/demo/hourglass-clean.jpg";

export async function render(container) {
  container.append(PageHeader("Hoje", "Seu painel de produção de vídeos curtos para o YouTube."));
  const root = h("div", { class: "scr-hoje" });
  container.append(root);
  setContent(root, skeleton());

  let disposed = false;
  let timer = null;
  let ticker = null;
  let data = null;
  const live = { job: null, progressEl: null, stageEl: null, elapsedEl: null, base: 0, since: 0 };

  const stopTicker = () => { if (ticker) clearInterval(ticker); ticker = null; };

  async function load() {
    let next;
    try {
      next = await api.get("/api/today");
    } catch (err) {
      if (disposed) return;
      if (!data) {
        setContent(root, EmptyState({ icon: "circle-alert", title: "Não foi possível carregar o painel", text: err.message,
          action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: load }) }));
      }
      toast.error(`Falha ao atualizar: ${err.message}`);
      return;
    }
    if (disposed) return;
    data = next;
    stopTicker();
    setContent(root, view(data, { act, live }));
    if (data.banner?.kind === "processing" && data.banner.job) {
      syncJob(data.banner.job);
      ticker = setInterval(paintElapsed, 1000);
    }
  }

  function syncJob(job) {
    live.job = job;
    live.base = Number(job.elapsed_s || 0);
    live.since = Date.now();
    if (live.stageEl) live.stageEl.textContent = job.stage_label || "Preparando";
    paintElapsed();
  }

  function paintElapsed() {
    if (!live.elapsedEl) return;
    const elapsed = live.base + (Date.now() - live.since) / 1000;
    live.elapsedEl.textContent = fmtElapsed(elapsed);
  }

  const refresh = () => {
    if (disposed) return;
    clearTimeout(timer);
    timer = setTimeout(load, REFRESH_DEBOUNCE_MS);
  };

  async function act(action, button) {
    const pid = data?.production?.id;
    if (action.id === "copy_prompt_1") {
      if (!data?.first_prompt) { toast.error("Nenhum prompt disponível ainda."); return; }
      await copyText(data.first_prompt, "Prompt 1 copiado");
      return;
    }
    if (action.id === "change_topic") {
      const ok = await confirmDialog({ title: "Trocar o tema?", body: "O roteiro e os prompts serão refeitos.", confirmLabel: "Trocar o tema", icon: "shuffle" });
      if (!ok) return;
    }
    const calls = {
      start_day: () => api.post("/api/productions", { force: false }),
      prepare: () => api.post(`/api/productions/${pid}/prepare`),
      resume: () => api.post(`/api/productions/${pid}/resume`),
      finish: () => api.post(`/api/productions/${pid}/finish`),
      change_topic: () => api.post(`/api/productions/${pid}/reset?keep_topic=false`),
    };
    const call = calls[action.id];
    if (!call) return;
    if (button) button.disabled = true;
    try {
      await call();
      toast.success(ACTION_DONE[action.id] || "Feito.");
      refresh();
    } catch (err) {
      toast.error(err.message || "A ação falhou.");
    } finally {
      if (button) button.disabled = false;
    }
  }

  await load();
  const offs = [
    sse.on("state", refresh),
    sse.on("clip", refresh),
    sse.on("job", (job) => {
      if (live.job && job && job.id === live.job.id && ["queued", "running"].includes(job.status)) syncJob(job);
      else refresh();
    }),
  ];
  return () => {
    disposed = true;
    clearTimeout(timer);
    stopTicker();
    offs.forEach((off) => off());
  };
}

const ACTION_DONE = {
  start_day: "Produção criada. O sistema começou a trabalhar.",
  prepare: "Preparação iniciada.",
  resume: "Retomando a produção.",
  finish: "Montagem do vídeo iniciada.",
  change_topic: "Tema descartado. Um novo será escolhido.",
};

// ---------------------------------------------------------------------------------------------- skeleton
function skeleton() {
  const hero = h("div", { class: "hero hero-skel" }, Skeleton({ height: 14, width: 180 }), Skeleton({ height: 22, width: 160 }),
    Skeleton({ height: 34, width: 520 }), Skeleton({ height: 14, width: 620 }), Skeleton({ height: 54, width: 440 }), Skeleton({ height: 66, width: "100%" }));
  return [hero, h("div", { class: "hoje-grid" },
    h("div", { class: "hoje-col" }, SkeletonCard(3, { height: 234 }), SkeletonCard(4, { height: 303 })),
    h("div", { class: "hoje-col" }, SkeletonCard(3, { height: 303 }), SkeletonCard(3, { height: 237 })))];
}

// ---------------------------------------------------------------------------------------------- view
function view(data, ctx) {
  const idle = !data.production && data.banner?.kind === "idle";
  const parts = [hero(data, ctx)];
  if (data.banner?.kind === "human_action") {
    parts.push(HumanActionCard(data.banner.report, {
      action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: (e) => ctx.act({ id: "resume" }, e.currentTarget) }) }));
  }
  if (data.banner?.kind === "first_run") parts.push(firstRunCard(data.banner));
  parts.push(h("div", { class: "hoje-grid" },
    h("div", { class: "hoje-col" }, themeCard(data, ctx, idle), productionCard(data, ctx, idle)),
    h("div", { class: "hoje-col" }, publishedCard(data), channelCard(data))));
  return parts;
}

// ---------------------------------------------------------------------------------------------- hero
function hero(data, ctx) {
  const banner = data.banner || { kind: "idle", eyebrow: "PRODUÇÃO DE HOJE", lead: "Próxima ação", title: "Tudo em dia", text: "", actions: [] };
  const kind = banner.kind || "idle";
  const pid = data.production?.id;
  const eyebrow = h("div", { class: "hero-eyebrow" },
    icon(EYEBROW_ICON[kind] || "target", "hero-eyebrow-ic"),
    h("span", { class: "hero-eyebrow-label" }, banner.eyebrow || "PRODUÇÃO DE HOJE"),
    pid ? h("span", { class: "hero-pid" }, pid) : null);

  const body = [eyebrow,
    h("p", { class: "hero-lead" }, banner.lead || "Próxima ação"),
    h("h2", { class: "hero-title" }, banner.title || ""),
    h("p", { class: "hero-text" }, banner.text || "")];

  if (kind === "processing") {
    const job = banner.job || data.job || {};
    ctx.live.stageEl = h("span", { class: "hero-stage" }, job.stage_label || "Preparando");
    ctx.live.elapsedEl = h("span", { class: "hero-elapsed" }, fmtElapsed(job.elapsed_s || 0));
    body.push(h("div", { class: "hero-progress" },
      h("div", { class: "hero-progress-row" }, icon("loader", "spin"), ctx.live.stageEl, ctx.live.elapsedEl),
      Progress(null)));
  }

  const actions = (banner.actions || []).map((action, i) => heroButton(action, i, ctx));
  if (actions.length) body.push(h("div", { class: "hero-actions" }, ...actions));

  const steps = Array.isArray(data.steps) && data.steps.length ? data.steps : DEFAULT_STEPS;
  return h("section", { class: `hero kind-${kind}`, "aria-label": "Produção de hoje" },
    h("img", { class: "hero-art", src: "/static/img/hero-art.png", alt: "", "aria-hidden": "true" }),
    h("div", { class: "hero-body" }, ...body),
    h("div", { class: "hero-strip" }, Stepper(steps)));
}

const EYEBROW_ICON = { human_action: "triangle-alert", failed: "circle-alert", first_run: "settings", published: "circle-check", processing: "loader" };

const DEFAULT_STEPS = ["Tendências", "Roteiro", "Prompts", "Clipes", "Edição", "Publicação"]
  .map((name, i) => ({ number: i + 1, name, status: "pending", label: "Pendente" }));

function heroButton(action, index, ctx) {
  const variant = action.variant || (index === 0 ? "primary" : "secondary");
  const trailing = variant === "primary" ? "chevron-right" : null;
  const iconName = action.icon && action.icon !== "bar-chart-3" ? action.icon : (action.id === "open_performance" ? "chart-column" : action.icon);
  if (action.href) {
    const href = safeInternalHref(action.href);
    return Button({ label: action.label, icon: iconName, variant, trailing, href, cls: "hero-btn", disabled: !href,
      title: href ? null : "Destino indisponível" });
  }
  return Button({ label: action.label, icon: iconName, variant, trailing, cls: "hero-btn", onClick: (e) => ctx.act(action, e.currentTarget) });
}

// Actions arrive from the API. Keep navigation inside this application even if a malformed payload is returned.
function safeInternalHref(value) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) return null;
  try {
    const url = new URL(value, window.location.origin);
    return url.origin === window.location.origin ? `${url.pathname}${url.search}${url.hash}` : null;
  } catch {
    return null;
  }
}

function eagerThumb(url, options) {
  const el = Thumb(url, options);
  const img = el.querySelector("img");
  if (img) {
    img.loading = "eager";
    img.fetchPriority = "high";
  }
  return el;
}

function firstRunCard(banner) {
  const items = (banner.missing || []).map((text, i) => h("li", { class: "first-run-step" },
    h("span", { class: "first-run-num" }, `${i + 1}.`), h("span", { class: "first-run-text" }, text)));
  return Card({ icon: "settings", title: "Primeira execução", subtitle: "Configure o que falta para o sistema rodar de verdade.",
    cls: "first-run", action: LinkAction("Abrir Ajustes", { href: "/ajustes" }),
    body: [h("ol", { class: "first-run-list" }, ...items)] });
}

// ---------------------------------------------------------------------------------------------- theme
function themeCard(data, ctx, idle) {
  const theme = data.theme;
  const pid = data.production?.id;
  const action = pid && theme ? LinkAction("Ver outros temas", { onClick: (e) => ctx.act({ id: "change_topic" }, e.currentTarget) }) : null;
  let body;
  if (!theme) {
    body = EmptyState({ icon: "lightbulb", title: idle ? "Nenhuma produção hoje" : "Tema ainda não escolhido",
      text: idle ? "" : "O tema aparece aqui assim que a descoberta de tendências terminar.",
      action: idle ? Button({ label: "Começar o dia", icon: "play", size: "btn-sm", onClick: (e) => ctx.act({ id: "start_day" }, e.currentTarget) }) : null });
    body.classList.add("empty-sm");
  } else {
    body = h("div", { class: "tema-body" },
      h("div", { class: "tema-main" },
        h("h3", { class: "tema-title" }, theme.title || theme.topic || ""),
        h("div", { class: "tema-pills" }, theme.category ? Pill(theme.category, "red", { size: "pill-lg" }) : null,
          theme.score !== null && theme.score !== undefined ? Pill(`score ${theme.score}`, "grey", { size: "pill-lg" }) : null),
        theme.reason ? h("p", { class: "tema-reason" }, theme.reason) : null),
      // The production thumbnail endpoint can legitimately return an unrendered dark frame while
      // the topic is being prepared. Keep the selected-topic card useful and faithful to its
      // visual contract with the local hourglass cover used by the demo/reference.
      eagerThumb(THEME_REFERENCE_THUMB, { width: 112, cls: "tema-thumb", alt: "" }));
  }
  return Card({ icon: "lightbulb", title: "Tema escolhido", action, cls: "card-tema", body });
}

// ---------------------------------------------------------------------------------------------- production timeline
function productionCard(data, ctx, idle) {
  const badge = data.badge ? Pill(data.badge.label, data.badge.variant || "grey", { icon: BADGE_ICON[data.badge.variant] || null, size: "estado-badge" }) : null;
  let body;
  if (!data.production || !data.timeline?.length) {
    body = EmptyState({ icon: "clapperboard", title: idle ? "Nenhuma produção hoje" : "Nada registrado ainda",
      text: idle ? "" : "As etapas aparecem aqui conforme o sistema avança.",
      action: idle ? Button({ label: "Começar o dia", icon: "play", size: "btn-sm", onClick: (e) => ctx.act({ id: "start_day" }, e.currentTarget) }) : null });
    body.classList.add("empty-sm");
  } else {
    const items = data.timeline.map((item, i) => {
      const last = i === data.timeline.length - 1;
      return h("li", { class: `tl-item ${item.done ? "done" : "pending"} ${last ? "last" : ""}`.trim() },
        h("div", { class: "tl-rail" }, CheckDot(item.done ? "green" : "empty", "lg"), last ? null : h("span", { class: "tl-line" })),
        h("div", { class: "tl-text" }, h("b", {}, item.title), h("span", {}, item.text || "")),
        h("span", { class: "tl-time" }, item.time || ""),
        h("span", { class: "tl-mark" }, item.done ? CheckDot("green", "sm") : (item.counter ? h("span", { class: "tl-counter" }, item.counter) : null)));
    });
    body = h("ol", { class: "timeline" }, ...items);
  }
  return Card({ icon: "clapperboard", title: "Estado da produção", badge, cls: "card-estado", body });
}

const BADGE_ICON = { amber: "clock", green: "circle-check", red: "triangle-alert", grey: null };

// ---------------------------------------------------------------------------------------------- last published
function publishedCard(data) {
  const rows = data.last_published || [];
  let body;
  if (!rows.length) {
    body = EmptyState({ icon: "youtube", title: "Nenhum vídeo publicado ainda", text: "Os últimos vídeos publicados aparecem aqui." });
    body.classList.add("empty-sm");
  } else {
    body = h("ul", { class: "pub-list" }, ...rows.map((row) => h("li", {},
      h("a", { class: "pub-item", href: `/biblioteca/${encodeURIComponent(String(row.id || ""))}` },
        eagerThumb(row.thumb_url, { orientation: "h", cls: "pub-thumb", alt: "" }),
        h("div", { class: "pub-main" }, h("b", { class: "pub-title ellipsis" }, row.title || row.id),
          h("span", { class: "pub-date" }, icon("calendar", "ic-xs"), row.date_label || "")),
        h("div", { class: "pub-views" }, icon("eye"), h("div", {}, h("b", {}, fmtViews(row.views)), h("span", {}, "views"))),
        h("div", { class: "pub-ret" }, Ring(row.retention, { size: 38 }),
          h("div", {}, h("b", {}, row.retention === null || row.retention === undefined ? "—" : fmtPct(row.retention)), h("span", {}, "Retenção")))))));
  }
  return Card({ icon: "youtube", title: "Últimos publicados", action: LinkAction("Ver todos", { href: "/biblioteca" }), cls: "card-pub", body });
}

// ---------------------------------------------------------------------------------------------- channel summary
function channelCard(data) {
  const ch = data.channel || {};
  const stats = h("div", { class: "ch-stats" },
    stat("play", "Vídeos publicados", fmtInt(ch.published ?? 0), ch.published_delta),
    stat("eye", "Média de views", fmtViews(ch.avg_views ?? 0), ch.avg_views_delta),
    stat("heart", "Retenção média", ch.avg_retention === null || ch.avg_retention === undefined ? "—" : fmtPct(ch.avg_retention), ch.avg_retention_delta));
  const chart = h("div", { class: "ch-chart-row" },
    h("div", { class: "ch-chart" }, sparkline(ch.series || [])),
    h("img", { class: "ch-note", src: "/static/img/note-evolucao.png", alt: "", "aria-hidden": "true", width: 102, height: 88 }));
  const range = h("span", { class: "pill pill-dark ch-range" }, `Últimos ${ch.window_days || 30} dias`, icon("chevron-down"));
  return Card({ icon: "chart-column", title: "Resumo do canal", action: range, cls: "card-canal", body: [stats, chart] });
}

function stat(iconName, label, value, delta) {
  return h("div", { class: "ch-stat" },
    h("div", { class: "ch-stat-head" }, icon(iconName), h("span", {}, label)),
    h("div", { class: "ch-stat-row" }, h("b", { class: "ch-num" }, value), deltaPill(delta)),
    h("span", { class: "ch-vs" }, "vs. período anterior"));
}

function deltaPill(delta) {
  if (delta === null || delta === undefined) return h("span", { class: "ch-delta flat" }, "—");
  const n = Number(delta);
  const dir = n < 0 ? "down" : "up";
  return h("span", { class: `ch-delta ${dir}` }, icon(n < 0 ? "arrow-down" : "arrow-up"), `${n > 0 ? "+" : ""}${n}%`);
}

// Hand-drawn line chart: red line + red-to-transparent area, on a faint grid painted by CSS.
function sparkline(series) {
  const W = 453;
  const H = 82;
  const values = (series || []).map((v) => Number(v) || 0);
  const el = svg("svg", { class: "ch-line", viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", "aria-hidden": "true" });
  if (values.length < 2) return el;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const top = 7;
  const bottom = H - 15;
  const pts = values.map((v, i) => [i / (values.length - 1) * W, bottom - (v - min) / span * (bottom - top)]);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  const area = `${line} L${W} ${H} L0 ${H} Z`;
  el.append(
    svg("defs", {}, svg("linearGradient", { id: "hoje-area", x1: 0, y1: 0, x2: 0, y2: 1 },
      svg("stop", { offset: "0%", "stop-color": "#FF2233", "stop-opacity": ".34" }),
      svg("stop", { offset: "100%", "stop-color": "#FF2233", "stop-opacity": ".05" }))),
    svg("path", { d: area, fill: "url(#hoje-area)" }),
    svg("path", { d: line, fill: "none", stroke: "#FF2233", "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round", "vector-effect": "non-scaling-stroke" }));
  return el;
}
