// Estúdio: stepper + the five production steps (roteiro, prompts, clipes, revisão, publicar).
import { h, icon, svg, on } from "../dom.js";
import { api } from "../api.js";
import { router } from "../router.js";
import { sse } from "../sse.js";
import { fmtSeconds, fmtBytes, fmtElapsed } from "../format.js";
import { PageHeader } from "../components/header.js";
import { Card, Pill, Button, LinkAction, NumCircle, CheckDot, Thumb, setContent } from "../components/ui.js";
import { EmptyState, Skeleton, SkeletonCard, Progress, HumanActionCard } from "../components/states.js";
import { toast, confirmDialog, copyText } from "../components/feedback.js";

const TITLE = "Estúdio";
const SUBTITLE = "Do roteiro à publicação. Produza seu vídeo completo, passo a passo.";
const ACCEPT = "video/mp4,video/quicktime,video/x-matroska,video/webm,.mp4,.mov,.mkv,.webm";
const VISIBILITY = [["private", "Privado"], ["unlisted", "Não listado"], ["public", "Público"], ["scheduled", "Agendado"]];
const CONTINUITY = "Gere a cena 1 primeiro. Nas seguintes, use Extend ou o último quadro como imagem inicial. Nunca recomece a cena.";

function safePublishedUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const raw = value.trim();
  try {
    const url = new URL(raw, window.location.origin);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    // A path belongs to this app; an absolute URL may only use a web protocol.
    if (raw.startsWith("//") || (url.origin !== window.location.origin && !/^https?:\/\//i.test(raw))) return null;
    return raw;
  } catch {
    return null;
  }
}

function eagerThumb(url, options) {
  const thumb = Thumb(url, options);
  // The production screenshots and the visual prompt list are above the fold.
  // Avoid lazy-loading them after the first paint, which made the reference view
  // temporarily fall back to the generic logo.
  const image = thumb.querySelector("img");
  if (image) image.loading = "eager";
  return thumb;
}

export async function render(container, params, query) {
  container.append(PageHeader(TITLE, SUBTITLE));
  const root = h("div", { class: "scr-estudio" });
  container.append(root);

  const id = params?.id || null;
  if (!id) return renderNoId(root);

  const ctx = {
    id, root, data: null, job: null,
    step: Number(query?.get("step")) || null,
    openScene: 1,
    uploads: new Map(),      // scene -> { frac, error }
    cleanups: [],
    ticker: null,
  };

  setContent(root, skeleton());
  await load(ctx);

  const same = (payload) => !payload?.production_id || payload.production_id === id;
  ctx.cleanups.push(sse.on("job", (job) => {
    if (!same(job)) return;
    ctx.job = job;
    if (["done", "failed", "human_action"].includes(job.status)) { ctx.job = null; load(ctx); return; }
    updateJobBars(ctx);
  }));
  ctx.cleanups.push(sse.on("clip", (p) => { if (same(p)) load(ctx); }));
  ctx.cleanups.push(sse.on("state", (p) => { if (same(p) && !p.deleted) load(ctx); }));
  ctx.cleanups.push(on(document, "click", (event) => {
    if (!event.target.closest(".clip-menu-wrap")) root.querySelectorAll(".clip-menu").forEach((m) => m.remove());
  }));

  return () => {
    ctx.cleanups.forEach((off) => off());
    if (ctx.ticker) clearInterval(ctx.ticker);
  };
}

/* ---------------- no id: today's production or an empty state ---------------- */

async function renderNoId(root) {
  setContent(root, skeleton());
  try {
    const today = await api.get("/api/today");
    const pid = today?.production?.id;
    if (pid) { router.navigate(`/estudio/${pid}`, { replace: true }); return () => {}; }
  } catch (err) {
    toast.error(err.message || "Não foi possível carregar a produção de hoje.");
  }
  setContent(root, h("section", { class: "card" }, EmptyState({
    icon: "clapperboard", title: "Nenhuma produção em andamento",
    text: "Comece o dia para escolher um tema, gerar o roteiro e os prompts das 5 cenas.",
    action: Button({ label: "Começar o dia", icon: "sparkles", onClick: async (event) => {
      event.currentTarget.disabled = true;
      try {
        const res = await api.post("/api/productions", { force: false });
        if (res?.id) router.navigate(`/estudio/${res.id}`); else toast.info("Produção iniciada.");
      } catch (err) { toast.error(err.message); event.currentTarget.disabled = false; }
    } }),
  })));
  return () => {};
}

/* ---------------- data ---------------- */

async function load(ctx) {
  try {
    ctx.data = await api.get(`/api/productions/${ctx.id}`);
    if (ctx.data.job && ["queued", "running"].includes(ctx.data.job.status)) ctx.job = ctx.data.job;
    draw(ctx);
  } catch (err) {
    toast.error(err.message);
    setContent(ctx.root, h("section", { class: "card" }, EmptyState({
      icon: "circle-alert", title: err.status === 404 ? "Produção não encontrada" : "Algo deu errado", text: err.message,
      action: Button({ label: "Voltar para Hoje", icon: "house", variant: "secondary", href: "/" }) })));
  }
}

function skeleton() {
  return h("div", { class: "stack" },
    h("section", { class: "card", style: { padding: "16px 22px" } }, Skeleton({ height: 36, width: "70%" })),
    h("div", { class: "grid grid-12" }, h("div", { class: "col-8" }, SkeletonCard(5, { height: 560 })), h("div", { class: "col-4 stack" }, SkeletonCard(3, { height: 260 }), SkeletonCard(2, { height: 170 }))),
    SkeletonCard(2, { height: 220 }));
}

/* ---------------- layout ---------------- */

function draw(ctx) {
  const d = ctx.data;
  const step = Math.min(5, Math.max(1, ctx.step || d.step || 1));
  const parts = [stepperCard(ctx, step)];
  if (d.human_action) {
    parts.push(HumanActionCard(d.human_action, { action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: () => runAction(ctx, "resume", "Retomando a produção…") }) }));
  }
  if (d.error && d.state === "FAILED") parts.push(h("div", { class: "notice red" }, icon("circle-alert"), h("span", {}, d.error)));

  if (step === 1) parts.push(h("div", { class: "est-split" }, scriptCard(ctx), h("div", { class: "stack" }, summaryCard(ctx))));
  else if (step === 2 || step === 3) {
    parts.push(h("div", { class: "est-split" }, promptsCard(ctx), h("div", { class: "stack" }, summaryCard(ctx), quickActionsCard(ctx))));
    parts.push(clipsCard(ctx));
  } else if (step === 4) parts.push(h("div", { class: "est-split rev" }, videoCard(ctx), qualityCard(ctx)));
  else parts.push(h("div", { class: "est-split" }, publishCard(ctx), h("div", { class: "stack" }, summaryCard(ctx))));

  setContent(ctx.root, h("div", { class: "stack" }, ...parts));
  updateJobBars(ctx);
}

function goStep(ctx, n) {
  router.navigate(`/estudio/${ctx.id}?step=${n}`);
}

/* ---------------- stepper ---------------- */

function stepperCard(ctx, active) {
  const d = ctx.data;
  const track = h("div", { class: "st-track" });
  (d.steps || []).forEach((s, i) => {
    const status = s.number === active && s.status !== "pending" ? "current" : (s.number === active ? "current" : s.status);
    const clickable = s.status !== "pending";
    const circle = h("span", { class: `st-circle ${status}` }, status === "done" ? icon("check") : String(s.number));
    const inner = [circle, status === "done" ? h("span", { class: "st-num-ghost" }, String(s.number)) : null,
      h("span", { class: "st-text" }, h("b", {}, s.name), h("span", {}, stepLabel(s, status)))];
    const el = clickable
      ? h("button", { class: `st-step ${status}`, type: "button", "aria-current": s.number === active ? "step" : null, onClick: () => goStep(ctx, s.number) }, ...inner)
      : h("div", { class: `st-step ${status}`, "aria-disabled": "true" }, ...inner);
    track.append(el);
    if (i < d.steps.length - 1) track.append(h("span", { class: `st-line ${s.status !== "pending" ? "on" : ""}` }));
  });
  return h("section", { class: "card st-card" }, track,
    h("div", { class: "st-prod" }, h("span", { class: "st-prod-label" }, "PRODUÇÃO"), h("span", { class: "st-prod-id" }, d.id)));
}

function stepLabel(s, status) {
  if (status === "current" && s.status === "done") return "Concluído";
  return s.label || (status === "done" ? "Concluído" : status === "current" ? "Em andamento" : "Pendente");
}

/* ---------------- summary + quick actions ---------------- */

function summaryCard(ctx) {
  const d = ctx.data;
  const tone = statusTone(d);
  const stat = (name, label, value, cls = "") => h("div", { class: `sum-stat ${cls}`.trim() },
    h("div", { class: "sum-stat-head" }, name === "smartphone" ? phoneIcon() : icon(name), h("span", {}, label)), h("div", { class: "sum-stat-value" }, value));
  const scenes = d.scenes || 5;
  const secs = Number(d.scene_seconds || 8);
  return Card({
    icon: "chart-column", title: "Resumo da produção", cls: "sum-card",
    action: LinkAction("Editar tema", { onClick: () => editTopic(ctx) }),
    body: [
      h("div", { class: "sum-top" }, eagerThumb(d.thumb_url, { cls: "sum-thumb", alt: "" }),
        h("div", { class: "sum-meta" }, h("span", { class: "sum-label" }, "Tema"), h("h3", { class: "sum-title" }, d.title || d.topic || "—"),
          d.category ? Pill(d.category, "red-solid", { size: "sum-pill" }) : null)),
      h("div", { class: "sum-stats" },
        stat("clock", "Duração total", `${Math.round(d.duration_total_s || scenes * secs)} segundos`),
        stat("smartphone", "Formato", [h("span", {}, d.format || "9:16"), h("span", { class: "sub" }, "(Vertical)")]),
        stat(tone.icon, "Status atual", d.state_label || d.state, `tone-${tone.color}`),
        stat("film", "Cenas", [h("span", {}, `${scenes} cenas`), h("span", { class: "sub" }, `(${Math.round(secs)}s cada)`)])),
    ],
  });
}

function phoneIcon() {
  // Lucide "smartphone" is not in icons.svg; drawn inline.
  return svg("svg", { class: "ic", viewBox: "0 0 24 24", "aria-hidden": "true" },
    svg("rect", { x: 5, y: 2, width: 14, height: 20, rx: 2, ry: 2 }), svg("path", { d: "M12 18h.01" }));
}

function statusTone(d) {
  const kind = String(d.status_kind || "");
  if (d.human_action || d.state === "FAILED" || kind.includes("fail") || kind.includes("human")) return { color: "red", icon: "triangle-alert" };
  if (d.upload || kind.includes("publish") || kind.includes("done") || kind.includes("learn")) return { color: "green", icon: "circle-check" };
  if (d.state === "READY" || kind.includes("ready")) return { color: "green", icon: "circle-check" };
  return { color: "amber", icon: "loader" };
}

function quickActionsCard(ctx) {
  const d = ctx.data;
  const allClips = (d.clips_received || 0) >= 5;
  const item = (btn, hint) => h("div", { class: "qa-item" }, btn, h("p", { class: "qa-hint" }, hint));
  return Card({
    icon: "zap", title: "Ações rápidas", cls: "qa-card",
    body: h("div", { class: "qa-grid" },
      item(Button({ label: "Copiar todos", icon: "copy", variant: "secondary", onClick: () => copyAll(d) }), "Copia todos os prompts das 5 cenas"),
      item(Button({ label: "Baixar roteiro", icon: "download", variant: "secondary", href: `/api/productions/${d.id}/script.txt`, cls: "qa-download" }), "Baixa o roteiro em TXT com todos os prompts"),
      item(Button({ label: "Ir para revisão", icon: "play", variant: "secondary", disabled: !allClips, onClick: () => continueToReview(ctx) }),
        allClips ? "Valida os clipes e monta o vídeo final" : "Disponível quando todos os clipes forem enviados")),
  });
}

function copyAll(d) {
  const text = (d.prompts || []).map((p) => `===== SCENE ${p.scene} =====\n${p.text}`).join("\n\n");
  if (!text) { toast.error("Ainda não há prompts para copiar."); return; }
  copyText(text, "Prompts das 5 cenas copiados");
}

/* ---------------- step 1: roteiro ---------------- */

function scriptCard(ctx) {
  const d = ctx.data;
  const s = d.script;
  if (!s) {
    return Card({ icon: "file-text", title: "Roteiro", subtitle: "Ainda não gerado", body: EmptyState({ icon: "file-text", title: "Roteiro ainda não gerado",
      text: "O roteiro é escrito automaticamente depois da escolha do tema.", action: Button({ label: "Gerar roteiro", icon: "sparkles", onClick: () => runAction(ctx, "prepare", "Gerando roteiro e prompts…") }) }) });
  }
  const sub = [s.hook_label, s.ending_label, s.est_duration_s != null ? `${Math.round(s.est_duration_s)}s` : null, s.total_words != null ? `${s.total_words} palavras` : null].filter(Boolean).join(" · ");
  const beats = (s.beats || []).map((b) => h("div", { class: "beat" },
    h("div", { class: "beat-head" }, h("span", { class: "beat-time" }, `${fmtS(b.start_s)} → ${fmtS(b.end_s)}`), Pill(b.purpose_label || b.purpose || "—", "dark", { size: "pill-sm" })),
    h("p", { class: "beat-text" }, b.narration || "—"),
    b.on_screen_note ? h("p", { class: "beat-note" }, icon("captions", "ic-xs"), b.on_screen_note) : null));
  return Card({
    icon: "file-text", title: "Roteiro", subtitle: sub, cls: "script-card",
    action: LinkAction("Refazer roteiro", { icon: "refresh-cw", onClick: () => redoScript(ctx) }),
    body: [s.title_working && s.title_working !== d.title ? h("p", { class: "script-working" }, h("span", {}, "Título de trabalho"), s.title_working) : null,
      h("div", { class: "beats" }, ...beats)],
    foot: h("div", { class: "row between" }, h("span", {}, `${(s.beats || []).length} batidas · o roteiro vira 5 prompts de 8 segundos`),
      Button({ label: "Ver os prompts", variant: "secondary", size: "btn-sm", trailing: "chevron-right", onClick: () => goStep(ctx, 2) })),
  });
}

function fmtS(v) { return `${Math.round(Number(v) || 0)}s`; }

/* ---------------- step 2: prompts ---------------- */

function promptsCard(ctx) {
  const d = ctx.data;
  const prompts = d.prompts || [];
  const list = h("div", { class: "pa-list" });
  if (!prompts.length) {
    list.append(EmptyState({ icon: "file-text", title: "Prompts ainda não gerados", text: "Os prompts das 5 cenas nascem do roteiro." }));
  }
  prompts.forEach((p) => list.append(promptRow(ctx, p, p.scene === ctx.openScene, list)));
  return Card({
    icon: "file-text", title: "Prompts para o Flow", subtitle: `${prompts.length || 5} cenas de ${Math.round(d.scene_seconds || 8)} segundos · continuidade obrigatória`, cls: "pa-card",
    action: LinkAction("Ver roteiro completo", { onClick: () => goStep(ctx, 1) }),
    body: [list, h("div", { class: "notice info pa-notice" }, icon("circle-alert", "red"), h("span", {}, CONTINUITY))],
  });
}

function promptRow(ctx, p, open, list) {
  const row = h("article", { class: `pa-row ${open ? "open" : ""}`, dataset: { scene: p.scene } });
  const toggle = () => {
    ctx.openScene = open ? null : p.scene;
    list.querySelectorAll(".pa-row").forEach((el) => el.replaceWith(promptRow(ctx, ctx.data.prompts.find((x) => String(x.scene) === el.dataset.scene), Number(el.dataset.scene) === ctx.openScene, list)));
  };
  const chev = h("button", { class: "pa-chev", type: "button", "aria-expanded": open ? "true" : "false", "aria-label": `${open ? "Recolher" : "Expandir"} cena ${p.scene}`, onClick: toggle }, icon(open ? "chevron-up" : "chevron-down"));
  const head = h("div", { class: "pa-head" },
    h("button", { class: "pa-toggle", type: "button", "aria-expanded": open ? "true" : "false", onClick: toggle },
      NumCircle(p.scene, open ? "red" : "outline"),
      h("span", { class: "pa-titles" }, h("b", {}, `Cena ${p.scene}`, h("span", { class: "sep" }, " · "), h("span", { class: "time" }, `${fmtS(p.start_s)} → ${fmtS(p.end_s)}`)), h("span", { class: "pa-label" }, p.label || ""))),
    Button({ label: "Copiar", icon: "copy", variant: "secondary", size: "btn-sm", onClick: () => copyText(p.text || "", `Prompt ${p.scene} copiado`) }),
    chev);
  const body = open ? h("div", { class: "pa-body" }, ...(p.blocks || []).map((b) => [h("span", { class: "pa-key" }, `${b.label}:`), h("span", { class: "pa-val" }, b.text)]).flat()) : null;
  // The API offers a thumb for every prompt, but the JPEG only exists once the scene's clip was received (404 otherwise).
  const clip = (ctx.data.clips || []).find((c) => c.scene === p.scene);
  const thumbUrl = clip?.present ? (clip.thumb_url || p.thumb_url) : null;
  row.append(eagerThumb(thumbUrl, { orientation: open ? "v" : "h", cls: "pa-thumb", alt: "" }), h("div", { class: "pa-main" }, head, body));
  return row;
}

/* ---------------- step 3: clips ---------------- */

function clipsCard(ctx) {
  const d = ctx.data;
  const clips = d.clips || [];
  const received = d.clips_received || 0;
  const input = h("input", { type: "file", accept: ACCEPT, multiple: true, class: "sr-only", "aria-label": "Selecionar clipes", onChange: (e) => { handleFiles(ctx, Array.from(e.target.files || [])); e.target.value = ""; } });
  const drop = h("button", { class: "dropzone", type: "button", onClick: () => input.click(),
    onDragover: (e) => { e.preventDefault(); drop.classList.add("over"); }, onDragleave: () => drop.classList.remove("over"),
    onDrop: (e) => { e.preventDefault(); drop.classList.remove("over"); handleFiles(ctx, Array.from(e.dataTransfer?.files || [])); } },
    icon("cloud-upload"), h("span", { class: "dz-text" }, h("b", {}, `Arraste os arquivos aqui · MP4 vertical · cerca de ${Math.round(d.scene_seconds || 8)} segundos`), h("span", {}, "ou clique para selecionar arquivos")));
  const row = h("div", { class: "clip-row" }, ...clips.map((c) => clipCard(ctx, c)));
  const warn = clips.find((c) => c.status === "warn" && c.warning);
  const canContinue = received >= 5 && !ctx.job;
  const foot = h("div", { class: "clip-foot" },
    warn ? h("div", { class: "notice amber clip-warn" }, icon("triangle-alert"), warnText(warn.warning)) : h("span", { class: "clip-foot-hint" }, received >= 5 ? "Todos os clipes foram recebidos." : `Faltam ${5 - received} clipe${5 - received > 1 ? "s" : ""} para continuar.`),
    Button({ label: "Continuar para revisão", trailing: "chevron-right", disabled: !canContinue, onClick: () => continueToReview(ctx) }));
  return Card({
    icon: "video", title: "Clipes gerados", cls: "clips-card",
    badge: h("span", { class: "clips-count" }, `${received} de ${clips.length || 5} recebidos`),
    action: LinkAction("Ver em grade", { icon: "layout-grid", trailing: null, onClick: () => row.classList.toggle("grid-view") }),
    body: [input, drop, row, jobBar(ctx), foot],
  });
}

function warnText(text) {
  // "Atenção na cena 3 — Duração 9,4s, …" -> bold "Atenção", "cena 3" and "Duração" like the reference.
  const m = /^(Atenção)( na )(cena \d+)( — )(\S+)([\s\S]*)$/.exec(text || "");
  if (!m) return h("span", {}, text);
  return h("span", {}, h("b", {}, m[1]), m[2], h("b", {}, m[3]), m[4], h("b", {}, m[5]), m[6]);
}

function clipCard(ctx, c) {
  const up = ctx.uploads.get(c.scene);
  const scene = c.scene;
  const pick = () => pickForScene(ctx, scene);
  const card = h("article", { class: `clip-card ${c.present ? c.status : "missing"} ${up ? "uploading" : ""}`.trim(), dataset: { scene } });
  const badge = c.present
    ? (c.status === "ok" ? CheckDot("green", "clip-badge") : h("span", { class: "clip-badge warn" }, icon("triangle-alert")))
    : h("span", { class: "clip-badge missing" }, icon("clock"));
  const meta = c.present
    ? h("span", { class: "clip-meta" }, h("span", { class: c.status === "warn" ? "red" : "" }, fmtSeconds(c.duration_s)), " · ", fmtBytes(c.size_bytes))
    : h("span", { class: "clip-meta" }, up ? "Enviando…" : (c.status_label || "Aguardando envio"));
  let actions;
  if (up) actions = h("div", { class: "clip-progress" }, Progress(up.frac), h("span", {}, `${Math.round((up.frac || 0) * 100)}%`));
  else if (c.present) {
    const menuWrap = h("div", { class: "clip-menu-wrap" });
    const kebab = h("button", { class: "kebab", type: "button", "aria-label": `Mais ações para a cena ${scene}`, "aria-haspopup": "menu", onClick: () => toggleMenu(ctx, menuWrap, c) }, icon("ellipsis-vertical"));
    menuWrap.append(kebab);
    actions = h("div", { class: "clip-actions" }, Button({ label: "Substituir", variant: "secondary", size: "btn-xs", cls: "clip-btn", onClick: pick }), menuWrap);
  } else actions = h("div", { class: "clip-actions" }, Button({ label: "Enviar arquivo", variant: "secondary", size: "btn-xs", cls: "clip-btn", onClick: pick }));
  card.append(
    c.present ? eagerThumb(c.thumb_url, { cls: "clip-thumb", alt: "" }) : h("div", { class: "clip-thumb clip-thumb-empty" }, icon("upload")),
    h("div", { class: "clip-body" }, h("div", { class: "clip-head" }, h("b", {}, c.name || `Cena ${scene}`), badge), meta, actions,
      up?.error ? h("span", { class: "clip-error" }, up.error) : null));
  return card;
}

function toggleMenu(ctx, wrap, c) {
  const existing = wrap.querySelector(".clip-menu");
  ctx.root.querySelectorAll(".clip-menu").forEach((m) => m.remove());
  if (existing) return;
  const menu = h("div", { class: "clip-menu", role: "menu" },
    h("button", { class: "clip-menu-item", type: "button", role: "menuitem", onClick: () => { menu.remove(); pickForScene(ctx, c.scene); } }, icon("upload", "ic-sm"), "Substituir"),
    h("button", { class: "clip-menu-item danger", type: "button", role: "menuitem", onClick: () => { menu.remove(); removeClip(ctx, c); } }, icon("trash", "ic-sm"), "Remover"));
  wrap.append(menu);
}

async function removeClip(ctx, c) {
  const ok = await confirmDialog({ title: `Remover o clipe da cena ${c.scene}?`, body: `${c.file || "O arquivo"} será apagado da caixa de entrada. Você poderá enviar outro no lugar.`, confirmLabel: "Remover", danger: true, icon: "trash" });
  if (!ok) return;
  try { await api.del(`/api/productions/${ctx.id}/clips/${c.scene}`); toast.success(`Clipe da cena ${c.scene} removido`); await load(ctx); }
  catch (err) { toast.error(err.message); }
}

function pickForScene(ctx, scene) {
  const input = h("input", { type: "file", accept: ACCEPT, class: "sr-only", "aria-label": `Arquivo para a cena ${scene}` });
  input.addEventListener("change", () => { const f = input.files?.[0]; input.remove(); if (f) uploadClip(ctx, scene, f); });
  ctx.root.append(input);
  input.click();
}

function handleFiles(ctx, files) {
  if (!files.length) return;
  const clips = ctx.data?.clips || [];
  const taken = new Set(clips.filter((c) => c.present).map((c) => c.scene));
  ctx.uploads.forEach((_, s) => taken.add(s));
  const plan = [];
  for (const file of files) {
    const m = /(?:^|\D)([1-5])(?!\d)/.exec(file.name.replace(/\.[^.]+$/, ""));
    let scene = m ? Number(m[1]) : null;
    if (scene === null || plan.some((p) => p.scene === scene)) {
      scene = [1, 2, 3, 4, 5].find((s) => !taken.has(s) && !plan.some((p) => p.scene === s)) ?? null;
    }
    if (scene === null) { toast.error(`Sem cena livre para ${file.name}. Substitua um clipe pelo botão do card.`); continue; }
    plan.push({ scene, file });
  }
  plan.forEach((p) => uploadClip(ctx, p.scene, p.file));
}

async function uploadClip(ctx, scene, file) {
  if (!/\.(mp4|mov|mkv|webm)$/i.test(file.name)) { toast.error(`${file.name}: envie MP4, MOV, MKV ou WEBM.`); return; }
  ctx.uploads.set(scene, { frac: 0, error: null });
  draw(ctx);
  const fd = new FormData();
  fd.append("scene", String(scene));
  fd.append("file", file, file.name);
  try {
    await api.upload(`/api/productions/${ctx.id}/clips`, fd, (frac) => {
      const u = ctx.uploads.get(scene); if (u) u.frac = frac;
      const bar = ctx.root.querySelector(`.clip-card[data-scene="${scene}"] .progress > span`);
      if (bar) bar.style.width = `${Math.round(frac * 100)}%`;
      const pct = ctx.root.querySelector(`.clip-card[data-scene="${scene}"] .clip-progress > span`);
      if (pct) pct.textContent = `${Math.round(frac * 100)}%`;
    });
    ctx.uploads.delete(scene);
    toast.success(`Clipe da cena ${scene} recebido`);
    await load(ctx);
  } catch (err) {
    ctx.uploads.delete(scene);
    toast.error(err.message || "Falha no envio.");
    await load(ctx);
    const card = ctx.root.querySelector(`.clip-card[data-scene="${scene}"]`);
    if (card) { card.classList.add("error"); card.querySelector(".clip-body")?.append(h("span", { class: "clip-error" }, err.message || "Falha no envio.")); }
  }
}

/* ---------------- step 4: revisão ---------------- */

function videoCard(ctx) {
  const d = ctx.data;
  const fv = d.final_video;
  const body = fv
    ? h("div", { class: "video-wrap" }, h("video", { controls: true, playsinline: true, preload: "metadata", src: fv.url, poster: d.thumb_url || null }))
    : EmptyState({ icon: "film", title: "Vídeo ainda não montado", text: (d.clips_received || 0) >= 5 ? "Os 5 clipes estão na caixa de entrada. Monte o vídeo final para revisar." : `Faltam ${5 - (d.clips_received || 0)} clipes. Envie-os no passo 3 antes de montar.`,
      action: Button({ label: "Montar o vídeo", icon: "clapperboard", disabled: !!ctx.job || (d.clips_received || 0) < 5, onClick: () => runAction(ctx, "finish", "Montando o vídeo…") }) });
  const sub = fv ? [fmtSeconds(fv.duration_s), d.format || "9:16"].join(" · ") : "Prévia do corte final";
  return Card({ icon: "square-play", title: "Vídeo final", subtitle: sub, cls: "video-card", body: [body, jobBar(ctx)] });
}

function qualityCard(ctx) {
  const d = ctx.data;
  const q = d.quality;
  let body;
  if (!q) body = EmptyState({ icon: "badge-check", title: "Sem verificações ainda", text: "O quality gate roda automaticamente quando o vídeo é montado: duração, resolução, codecs, áudio e continuidade." });
  else body = h("div", { class: "qg-list" }, ...q.checks.map((c) => h("div", { class: `qg-item ${c.passed ? "ok" : "fail"}` }, CheckDot(c.passed ? "green" : "red"),
    h("div", { class: "qg-text" }, h("b", {}, c.label), c.detail ? h("span", {}, c.detail) : null))));
  const verdict = q ? Pill(q.passed ? "Aprovado" : "Revisão necessária", q.passed ? "green" : "red", { icon: q.passed ? "check" : "triangle-alert", size: "pill-lg" }) : null;
  return Card({
    icon: "badge-check", title: "Quality gate", subtitle: q ? `${q.checks.filter((c) => c.passed).length} de ${q.checks.length} verificações aprovadas` : "Verificação automática do vídeo final", cls: "qg-card",
    badge: verdict, body,
    foot: h("div", { class: "row between" }, h("span", {}, d.can_publish ? "Tudo certo. O vídeo pode ir para a publicação." : "A publicação abre quando o vídeo passa no quality gate."),
      Button({ label: "Ir para publicação", trailing: "chevron-right", disabled: !d.can_publish, onClick: () => goStep(ctx, 5) })),
  });
}

/* ---------------- step 5: publicar ---------------- */

function publishCard(ctx) {
  const d = ctx.data;
  const m = d.metadata || {};
  const title = h("input", { class: "input", id: "pub-title", value: m.title || d.title || "", maxlength: 100 });
  const desc = h("textarea", { class: "textarea", id: "pub-desc", rows: 5 });
  desc.value = m.description || "";
  const tags = h("input", { class: "input", id: "pub-tags", value: (m.hashtags || []).join(", "), placeholder: "#Shorts, #ciência" });
  const vis = h("select", { class: "select", id: "pub-vis" }, ...VISIBILITY.map(([v, l]) => h("option", { value: v, selected: v === (d.upload?.privacy || d.visibility) }, l)));
  const hour = h("input", { class: "input", id: "pub-hour", type: "time", step: 3600, value: `${String(d.publish_hour_local ?? 18).padStart(2, "0")}:00` });
  const field = (label, control, hint = null) => h("div", { class: "field" }, h("label", { for: control.id }, label), control, hint ? h("span", { class: "hint" }, hint) : null);

  const collect = () => ({
    title: title.value.trim(), description: desc.value.trim(),
    hashtags: tags.value.split(/[,\s]+/).map((t) => t.trim()).filter(Boolean).map((t) => (t.startsWith("#") ? t : `#${t}`)).slice(0, 6),
    visibility: vis.value, publish_hour_local: Number(hour.value.split(":")[0]) || 0,
  });
  const save = async (btn) => {
    btn.disabled = true;
    try { await api.put(`/api/productions/${ctx.id}/metadata`, collect()); toast.success("Metadados salvos"); return true; }
    catch (err) { toast.error(err.message); return false; }
    finally { btn.disabled = false; }
  };
  const publish = async (event) => {
    const btn = event.currentTarget;
    const ok = await confirmDialog({ title: "Publicar no YouTube?", body: `"${collect().title}" será enviado como ${VISIBILITY.find(([v]) => v === vis.value)?.[1] || vis.value}. Os metadados atuais são salvos antes do envio.`, confirmLabel: "Publicar", icon: "youtube" });
    if (!ok) return;
    if (!(await save(btn))) return;
    await runAction(ctx, "publish", "Publicando no YouTube…", { confirm: true });
  };

  const publishedUrl = safePublishedUrl(d.upload?.url);
  const published = d.upload ? h("div", { class: "pub-done" }, Pill("Publicado", "green", { icon: "check" }),
    publishedUrl ? h("a", { class: "pub-link", href: publishedUrl, target: "_blank", rel: "noopener noreferrer" }, icon("external-link", "ic-sm"), publishedUrl) : null) : null;

  return Card({
    icon: "youtube", title: "Publicar", subtitle: "Título, descrição e hashtags do Short. Revise antes de enviar.", cls: "pub-card", badge: published,
    body: [
      !d.upload_enabled ? h("div", { class: "notice info pub-notice" }, icon("info"), h("span", {}, "A publicação automática está desligada em Ajustes. O botão abaixo publica manualmente, com a sua confirmação.")) : null,
      h("div", { class: "pub-form" },
        field("Título", title, `${(m.title || d.title || "").length} de 100 caracteres`),
        field("Descrição", desc),
        field("Hashtags", tags, "Separadas por vírgula · até 6"),
        h("div", { class: "pub-two" },
          field("Visibilidade", h("div", { class: "select-wrap" }, vis, icon("chevron-down"))),
          field("Horário", hour, "Hora cheia, no fuso local"))),
      jobBar(ctx),
    ],
    foot: h("div", { class: "row between" },
      h("span", {}, d.can_publish ? "Pronto para publicar." : d.upload ? "Este vídeo já foi publicado." : "A publicação abre quando o vídeo passa no quality gate."),
      h("div", { class: "row" },
        Button({ label: "Salvar", icon: "save", variant: "secondary", onClick: (e) => save(e.currentTarget) }),
        Button({ label: "Publicar no YouTube", icon: "youtube", disabled: !d.can_publish || !!ctx.job, onClick: publish }))),
  });
}

/* ---------------- actions & jobs ---------------- */

async function runAction(ctx, name, message, body = {}) {
  try {
    const res = await api.post(`/api/productions/${ctx.id}/${name}`, body);
    if (res?.job) ctx.job = res.job;
    toast.info(message);
    draw(ctx);
  } catch (err) { toast.error(err.message); }
}

function continueToReview(ctx) {
  const d = ctx.data;
  if (d.final_video) { goStep(ctx, 4); return; }
  runAction(ctx, "collect", "Validando os clipes e montando o vídeo…");
}

async function redoScript(ctx) {
  const ok = await confirmDialog({ title: "Refazer o roteiro?", body: "O roteiro e os prompts atuais serão descartados e escritos de novo com o mesmo tema. Os clipes já enviados continuam na caixa de entrada.", confirmLabel: "Refazer roteiro", danger: true, icon: "refresh-cw" });
  if (!ok) return;
  try { await api.post(`/api/productions/${ctx.id}/reset?keep_topic=true`); toast.info("Refazendo o roteiro…"); await load(ctx); }
  catch (err) { toast.error(err.message); }
}

async function editTopic(ctx) {
  const ok = await confirmDialog({ title: "Editar o tema?", body: "A produção volta ao início e um novo tema é escolhido. Roteiro, prompts e clipes atuais serão descartados.", confirmLabel: "Editar tema", danger: true, icon: "pencil" });
  if (!ok) return;
  try { await api.post(`/api/productions/${ctx.id}/reset?keep_topic=false`); toast.info("Escolhendo um novo tema…"); await load(ctx); }
  catch (err) { toast.error(err.message); }
}

function jobBar(ctx) {
  return h("div", { class: "job-bar", hidden: true },
    h("div", { class: "job-bar-head" }, icon("loader", "spin"), h("b", { class: "job-stage" }, ""), h("span", { class: "job-elapsed" }, "")),
    Progress(null));
}

function updateJobBars(ctx) {
  const job = ctx.job;
  const bars = ctx.root.querySelectorAll(".job-bar");
  bars.forEach((bar) => { bar.hidden = !job; });
  if (!job) { if (ctx.ticker) { clearInterval(ctx.ticker); ctx.ticker = null; } return; }
  const base = Number(job.elapsed_s || 0);
  const since = Date.now();
  const paint = () => {
    const elapsed = base + (Date.now() - since) / 1000;
    ctx.root.querySelectorAll(".job-stage").forEach((el) => { el.textContent = job.stage_label || job.name || "Trabalhando…"; });
    ctx.root.querySelectorAll(".job-elapsed").forEach((el) => { el.textContent = fmtElapsed(elapsed); });
  };
  paint();
  if (ctx.ticker) clearInterval(ctx.ticker);
  ctx.ticker = setInterval(paint, 1000);
}
