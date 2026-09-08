// Ajustes: six tabs over one settings form. The form lives in module memory so switching tabs
// (which re-renders the screen through the router) never loses what the operator typed.
import { h, icon } from "../dom.js";
import { api } from "../api.js";
import { router } from "../router.js";
import { sse } from "../sse.js";
import { PageHeader } from "../components/header.js";
import { Card, Button, CheckDot, setContent } from "../components/ui.js";
import { Skeleton, SkeletonCard, EmptyState } from "../components/states.js";
import { toast, confirmDialog } from "../components/feedback.js";

const TABS = [
  ["geral", "Geral", "settings"], ["ia", "IA", "sparkles"], ["youtube", "YouTube", "youtube"],
  ["marca", "Marca", "palette"], ["automacao", "Automação", "zap"], ["arquivos", "Arquivos", "folder"],
];
const VISIBILITY = [["public", "Público"], ["private", "Privado"], ["unlisted", "Não listado"], ["scheduled", "Agendado"]];
const TONES = ["Informativo e descontraído", "Sério e direto", "Divertido e rápido"];
const WATERMARKS = ["Logo OneMoreShort (canto inferior direito)", "Logo OneMoreShort (canto superior direito)", "Sem marca d'água"];
const HEALTH_ICONS = { server: "server", database: "database", ffmpeg: "cpu", youtube: "youtube", gemini: "sparkles", storage: "folder" };
const HEALTH_TONE = { ok: "ok", warn: "warn", error: "error" };
const FILE_ROWS = [
  ["project", "Pasta do projeto", "project_dir", false], ["inbox", "Clipes temporários", "inbox_dir", true],
  ["ffmpeg", "FFmpeg (executável)", "ffmpeg_binary", true], ["exports", "Exportações", "exports_dir", false],
];
const FORM_FIELDS = {
  ai: ["model"],
  publish: ["visibility", "publish_hour_local", "title_suffix", "description_template", "default_hashtags", "auto_publish"],
  brand: ["name", "tone", "cta", "watermark", "use_brand_identity"],
  rules: ["target_duration_s", "scenes", "cost_limit_usd", "safety_moderation", "avoid_sensitive", "auto_captions"],
  files: ["inbox_dir", "ffmpeg_binary"],
};

// Module memory (survives navigation between tabs). apiKey holds only what the operator typed.
const mem = { data: null, health: null, form: null, orig: null, apiKey: "", showKey: false };

export async function render(container, params) {
  container.append(PageHeader("Ajustes", "Configure seu ambiente, chaves de API, publicação e automação."));
  const root = h("div", { class: "scr-ajustes" });
  container.append(root);
  const ui = { root, tab: TABS.some(([id]) => id === params.tab) ? params.tab : "geral", saveBtn: null, alive: true };
  ui.redraw = () => draw(ui);

  if (!mem.data) {
    root.append(skeleton());
    try {
      await load();
    } catch (err) {
      if (!ui.alive) return () => {};
      toast.error(err.message);
      setContent(root, EmptyState({ icon: "circle-alert", title: "Não foi possível carregar os ajustes", text: err.message,
        action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: () => location.reload() }) }));
      return () => { ui.alive = false; };
    }
  }
  if (!ui.alive) return () => {};
  draw(ui);

  const refresh = async () => {
    try { await load(); if (ui.alive) draw(ui); } catch (err) { if (ui.alive) toast.error(err.message); }
  };
  const offSettings = sse.on("settings", refresh);
  const offJob = sse.on("job", (job) => {
    if (job?.name === "youtube-auth" && ["done", "finished", "failed", "error"].includes(job.status)) {
      if (job.status === "done" || job.status === "finished") toast.success("Conta do YouTube conectada.");
      else toast.error(job.error || "A autorização do YouTube não foi concluída.");
      refresh();
    }
  });
  return () => { ui.alive = false; offSettings(); offJob(); };
}

/* ---------- data ---------- */

async function load() {
  const [data, health] = await Promise.all([api.get("/api/settings"), api.get("/api/health").catch(() => null)]);
  absorb(data);
  if (health) mem.health = health;
}

function formFrom(data) {
  const out = {};
  for (const [section, keys] of Object.entries(FORM_FIELDS)) {
    out[section] = {};
    for (const key of keys) out[section][key] = data?.[section]?.[key] ?? null;
  }
  return out;
}

// Take fresh server values but keep the operator's unsaved edits (fields that differ from the old original).
function absorb(data, { reset = false } = {}) {
  const next = formFrom(data);
  if (!reset && mem.form && mem.orig) {
    for (const section of Object.keys(next)) {
      for (const key of Object.keys(next[section])) {
        if (!same(mem.form[section]?.[key], mem.orig[section]?.[key])) next[section][key] = mem.form[section][key];
      }
    }
  }
  mem.data = data;
  mem.orig = formFrom(data);
  mem.form = next;
  if (reset) { mem.apiKey = ""; mem.showKey = false; }
}

function same(a, b) {
  if (typeof a === "number" || typeof b === "number") return Number(a) === Number(b);
  return (a ?? "") === (b ?? "");
}

function diff() {
  const out = {};
  for (const [section, fields] of Object.entries(mem.form)) {
    const changed = {};
    for (const [key, value] of Object.entries(fields)) if (!same(value, mem.orig[section][key])) changed[key] = value;
    if (Object.keys(changed).length) out[section] = changed;
  }
  if (mem.apiKey.trim()) out.ai = { ...(out.ai || {}), api_key: mem.apiKey.trim() };
  return out;
}

function set(section, key, value, ui) {
  mem.form[section][key] = value;
  updateSave(ui);
}

function updateSave(ui) {
  if (!ui.saveBtn) return;
  const dirty = Object.keys(diff()).length > 0;
  ui.saveBtn.disabled = !dirty;
  ui.saveBtn.setAttribute("aria-disabled", String(!dirty));
}

/* ---------- layout ---------- */

function draw(ui) {
  const body = h("div", { class: "body" }, ...content(ui));
  setContent(ui.root, tabsBar(ui), body, footer(ui));
}

function skeleton() {
  return h("div", { class: "body loading" }, Skeleton({ height: 48 }),
    h("div", { class: "grid row1 sk" }, SkeletonCard(4, { height: 340 }), SkeletonCard(4, { height: 340 }), SkeletonCard(6, { height: 340 })),
    h("div", { class: "grid row2 sk" }, SkeletonCard(7, { height: 460 }), SkeletonCard(5, { height: 290 }), SkeletonCard(3, { height: 160 }), SkeletonCard(6, { height: 330 })));
}

function tabsBar(ui) {
  return h("div", { class: "tabs", role: "tablist", "aria-label": "Seções dos ajustes" },
    ...TABS.map(([id, label, ic]) => h("button", {
      class: "tab", role: "tab", type: "button", "aria-selected": String(ui.tab === id),
      onClick: () => { if (ui.tab !== id) router.navigate(`/ajustes/${id}`, { replace: true }); },
    }, icon(ic), h("span", {}, label))));
}

function content(ui) {
  switch (ui.tab) {
    case "ia": return [h("div", { class: "grid tab-ia" }, aiCard(ui), healthCard())];
    case "youtube": return [h("div", { class: "grid tab-youtube" }, youtubeCard(ui), publishCard(ui))];
    case "marca": return [h("div", { class: "grid tab-marca" }, brandCard(ui))];
    case "automacao": return [h("div", { class: "grid tab-automacao" }, rulesCard(ui), publishCard(ui))];
    case "arquivos": return [h("div", { class: "grid tab-arquivos" }, filesCard(ui))];
    default: return [
      h("div", { class: "grid row1" }, aiCard(ui), youtubeCard(ui), healthCard()),
      h("div", { class: "grid row2" }, publishCard(ui), brandCard(ui), filesCard(ui), rulesCard(ui)),
    ];
  }
}

function footer(ui) {
  const restore = Button({ label: "Restaurar padrões", icon: "rotate-ccw", variant: "secondary", cls: "foot-restore", onClick: () => restoreDefaults(ui) });
  const save = h("button", { class: "btn btn-primary foot-save", type: "button", onClick: () => saveAll(ui) },
    icon("save"), h("span", { class: "foot-save-main" }, "Salvar alterações"),
    h("span", { class: "foot-save-sub" }, "Aplicar todas as configurações."), icon("chevron-right", "trail"));
  ui.saveBtn = save;
  updateSave(ui);
  return h("div", { class: "foot" },
    h("div", { class: "foot-left" }, restore, h("span", { class: "foot-note" }, "Voltar para as configurações originais do sistema.")),
    save);
}

/* ---------- cards ---------- */

function statusPill(label, tone) {
  return h("span", { class: `pill pill-lg ${tone === "green" ? "pill-green-soft" : "pill-dark"}` }, h("span", { class: "pdot" }), label);
}

function desc(text) {
  return h("p", { class: "desc" }, text);
}

function aiCard(ui) {
  const ai = mem.data.ai;
  const keyInput = h("input", {
    class: "input key-input", type: mem.showKey ? "text" : "password", id: "aj-api-key", autocomplete: "off", spellcheck: "false",
    placeholder: ai.api_key_masked || "Cole a chave do Google AI Studio", value: mem.apiKey,
    onInput: (event) => { mem.apiKey = event.target.value; updateSave(ui); },
  });
  const eye = h("button", {
    class: "eye", type: "button", "aria-label": mem.showKey ? "Ocultar chave digitada" : "Mostrar chave digitada", "aria-pressed": String(mem.showKey),
    onClick: () => {
      mem.showKey = !mem.showKey;
      keyInput.type = mem.showKey ? "text" : "password";
      eye.setAttribute("aria-pressed", String(mem.showKey));
      eye.setAttribute("aria-label", mem.showKey ? "Ocultar chave digitada" : "Mostrar chave digitada");
      setContent(eye, icon(mem.showKey ? "eye-off" : "eye"));
    },
  }, icon(mem.showKey ? "eye-off" : "eye"));
  const models = (ai.models || []).map((m) => [m.value, m.label]);
  const conn = ai.connection || {};
  const testBtn = Button({ label: "Testar conexão", icon: "wifi", variant: "secondary", size: "btn-sm", onClick: () => testConnection(ui, testBtn) });
  const result = h("div", { class: `conn ${conn.ok ? "ok" : "bad"}` },
    CheckDot(conn.ok ? "green" : "red"),
    h("div", { class: "conn-text" }, h("b", {}, conn.message || (conn.ok ? "Conexão bem-sucedida!" : "Sem conexão")), conn.detail ? h("span", {}, conn.detail) : null),
    testBtn);
  return Card({
    icon: "sparkles", title: "Google AI Studio", cls: "c-ai",
    badge: ai.has_key ? statusPill("Conectado", "green") : statusPill("Sem chave", "grey"),
    body: [
      desc("Configure sua chave da API do Gemini para geração de roteiros, legendas e análise de conteúdo."),
      h("div", { class: "fields" },
        field("Chave da API", "aj-api-key", h("div", { class: "input-wrap" }, keyInput, eye)),
        field("Modelo padrão", "aj-ai-model", selectField(ui, "ai", "model", models)),
        result),
    ],
  });
}

function youtubeCard(ui) {
  const yt = mem.data.youtube;
  const acct = yt.account || {};
  const name = yt.connected ? (acct.name || "Conta do YouTube") : "Nenhuma conta conectada";
  const handle = yt.connected ? (acct.handle ? (acct.handle.startsWith("@") ? acct.handle : `@${acct.handle}`) : "—") : "Conecte para publicar";
  const allActive = (yt.scopes || []).length > 0 && yt.scopes.every((s) => s.active);
  const scopes = h("div", { class: "scopes" },
    ...(yt.scopes || []).map((s) => h("div", { class: "scope" }, CheckDot(s.active ? "green" : "empty"), h("span", {}, s.label))),
    allActive ? h("span", { class: "pill pill-green-soft" }, "Todos os escopos ativos")
      : h("span", { class: "pill pill-amber" }, yt.connected ? "Escopos pendentes" : "Escopos inativos"));
  const mainBtn = yt.connected
    ? Button({ label: "Reconectar conta", icon: "refresh-cw", variant: "secondary", size: "btn-sm", cls: "btn-block", onClick: () => connectYoutube(ui) })
    : Button({ label: "Conectar conta", icon: "youtube", variant: "primary", size: "btn-sm", cls: "btn-block", disabled: !yt.has_client_secret, onClick: () => connectYoutube(ui) });
  return Card({
    icon: "youtube", title: "YouTube OAuth", cls: "c-yt",
    badge: yt.connected ? statusPill("Conectado", "green") : statusPill("Desconectado", "grey"),
    body: [
      desc("Conecte sua conta do YouTube para publicar vídeos automaticamente."),
      h("div", { class: "acct" },
        h("span", { class: `avatar ${yt.connected ? "" : "off"}`, "aria-hidden": "true" }, yt.connected ? initial(acct.name) : icon("user")),
        h("div", { class: "acct-text" }, h("div", { class: "acct-name" }, name), h("div", { class: "acct-handle" }, handle),
          h("div", { class: "acct-subs" }, fmtSubs(acct.subscribers))),
        yt.connected ? Button({ label: "Desconectar", variant: "secondary", size: "btn-sm", onClick: () => disconnectYoutube(ui) }) : null),
      scopes,
      mainBtn,
      !yt.has_client_secret ? h("p", { class: "yt-hint" }, `Falta o client secret do Google em ${yt.client_secret_path || "secrets/"}.`) : null,
    ],
  });
}

function healthCard() {
  const items = mem.health?.items || [];
  const list = items.length
    ? h("div", { class: "hlist" }, ...items.map((it) => h("div", { class: "hrow" },
        h("span", { class: "hicon" }, icon(HEALTH_ICONS[it.key] || "circle")),
        h("span", { class: "hname" }, it.name),
        h("span", { class: `hstate ${HEALTH_TONE[it.status] || "warn"}` }, h("span", { class: "hdot" }), it.label || it.status))))
    : h("p", { class: "desc" }, "Não foi possível consultar a saúde do sistema.");
  return Card({ icon: "heart", title: "Saúde do sistema", cls: "c-health", body: [desc("Verifique o status dos principais serviços."), list] });
}

function publishCard(ui) {
  const p = mem.form.publish;
  const hour = Number.isInteger(p.publish_hour_local) ? p.publish_hour_local : 12;
  const time = h("input", {
    class: "input", type: "time", id: "aj-publish-hour", value: `${String(hour).padStart(2, "0")}:00`, step: 3600,
    onChange: (event) => { const hh = parseInt(event.target.value.split(":")[0], 10); if (!Number.isNaN(hh)) set("publish", "publish_hour_local", hh, ui); },
  });
  return Card({
    icon: "upload", title: "Publicação padrão", cls: "c-publish",
    body: [
      desc("Defina as configurações padrão para seus vídeos no YouTube."),
      h("div", { class: "fields tight" },
        h("div", { class: "two" },
          field("Visibilidade", "aj-publish-visibility", selectField(ui, "publish", "visibility", VISIBILITY)),
          field("Horário padrão de upload", "aj-publish-hour", h("div", { class: "input-wrap has-icon" }, icon("clock"), time))),
        field("Sufixo no título", "aj-publish-title_suffix", textField(ui, "publish", "title_suffix", { maxLength: 40 })),
        field("Modelo de descrição", "aj-publish-description_template", textArea(ui, "publish", "description_template")),
        field("Hashtags padrão", "aj-publish-default_hashtags", textField(ui, "publish", "default_hashtags", { maxLength: 300 }), "↳ Separe por vírgula"),
        toggle(ui, "publish", "auto_publish", "Publicação automática", "Publicar vídeos automaticamente após renderização.", "lg")),
    ],
  });
}

function brandCard(ui) {
  const b = mem.form.brand;
  return Card({
    icon: "palette", title: "Marca do canal", cls: "c-brand",
    body: [
      desc("Defina a identidade e o estilo de comunicação do seu canal."),
      h("div", { class: "brows" },
        brow("Nome do canal", "aj-brand-name", textField(ui, "brand", "name", { maxLength: 60 })),
        brow("Tom de voz", "aj-brand-tone", selectField(ui, "brand", "tone", withCurrent(TONES, b.tone))),
        brow("CTA padrão", "aj-brand-cta", textField(ui, "brand", "cta", { maxLength: 120 })),
        brow("Marca d'água", "aj-brand-watermark", selectField(ui, "brand", "watermark", withCurrent(WATERMARKS, b.watermark)))),
      checkbox(ui, "brand", "use_brand_identity", "Usar identidade visual nas miniaturas", "Aplicar o logo e estilo da marca automaticamente."),
    ],
  });
}

function rulesCard(ui) {
  const money = (v) => Number(v).toFixed(2).replace(".", ",");
  return Card({
    icon: "clapperboard", title: "Regras de produção", cls: "c-rules",
    body: [
      desc("Ajuste os parâmetros de geração dos vídeos."),
      h("div", { class: "srows" },
        sliderRow(ui, "rules", "target_duration_s", "Duração alvo (segundos)", 15, 60, 1, String),
        sliderRow(ui, "rules", "scenes", "Número de cenas", 3, 10, 1, String),
        sliderRow(ui, "rules", "cost_limit_usd", "Limite de custo por vídeo (USD)", 0.01, 1, 0.01, money)),
      h("div", { class: "toggles" },
        toggle(ui, "rules", "safety_moderation", "Usar moderação de conteúdo (safety)"),
        toggle(ui, "rules", "avoid_sensitive", "Evitar conteúdo sensível"),
        toggle(ui, "rules", "auto_captions", "Incluir legendas automaticamente", "Gerar e queimar legendas nos vídeos.")),
    ],
  });
}

function filesCard(ui) {
  return Card({
    icon: "folder", title: "Arquivos locais", cls: "c-files",
    body: [desc("Defina os diretórios utilizados pelo sistema."), h("div", { class: "frows" }, ...FILE_ROWS.map((row) => fileRow(ui, row)))],
  });
}

function fileRow(ui, [key, label, prop, editable]) {
  const id = `aj-file-${key}`;
  const input = h("input", {
    class: "input", type: "text", id, readonly: true, spellcheck: "false",
    value: (editable ? mem.form.files[prop] : mem.data.files[prop]) || "",
    onInput: (event) => { if (editable) set("files", prop, event.target.value, ui); },
  });
  const select = Button({ label: "Selecionar", icon: "folder", variant: "secondary", cls: "btn-file", onClick: () => {
    if (!editable) { toast.info("Este caminho é definido pelo sistema e não pode ser alterado aqui."); return; }
    input.removeAttribute("readonly");
    input.focus();
    input.select();
  } });
  const open = Button({ label: "Abrir", icon: "external-link", variant: "secondary", cls: "btn-file", onClick: async () => {
    try { await api.post("/api/settings/open-folder", { key }); toast.success("Pasta aberta neste computador."); }
    catch (err) { toast.error(err.message); }
  } });
  return h("div", { class: "frow" }, h("label", { for: id }, label), input, select, open);
}

/* ---------- field helpers ---------- */

function field(label, id, control, hint = null) {
  return h("div", { class: "field" }, h("label", { for: id }, label), control, hint ? h("span", { class: "hint" }, hint) : null);
}

function brow(label, id, control) {
  return h("div", { class: "brow" }, h("label", { for: id }, label), control);
}

function textField(ui, section, key, { maxLength = null } = {}) {
  return h("input", {
    class: "input", type: "text", id: `aj-${section}-${key}`, value: mem.form[section][key] ?? "", maxlength: maxLength, spellcheck: "false",
    onInput: (event) => set(section, key, event.target.value, ui),
  });
}

function textArea(ui, section, key) {
  const el = h("textarea", { class: "textarea", id: `aj-${section}-${key}`, rows: 3, maxlength: 2000, onInput: (event) => set(section, key, event.target.value, ui) });
  el.value = mem.form[section][key] ?? "";
  return el;
}

function selectField(ui, section, key, options) {
  const current = mem.form[section][key];
  const el = h("select", { class: "select", id: `aj-${section}-${key}`, onChange: (event) => set(section, key, event.target.value, ui) },
    ...options.map(([value, label]) => h("option", { value, selected: value === current }, label)));
  return h("div", { class: "select-wrap" }, el, icon("chevron-down"));
}

function withCurrent(list, current) {
  const options = list.map((v) => [v, v]);
  if (current && !list.includes(current)) options.unshift([current, current]);
  return options;
}

function toggle(ui, section, key, title, sub = null, size = "") {
  const input = h("input", { type: "checkbox", checked: !!mem.form[section][key], onChange: (event) => set(section, key, event.target.checked, ui) });
  return h("label", { class: `toggle ${size}`.trim() }, input, h("span", { class: "track" }),
    h("span", { class: "toggle-text" }, h("b", {}, title), sub ? h("span", {}, sub) : null));
}

function checkbox(ui, section, key, title, sub) {
  const input = h("input", { type: "checkbox", checked: !!mem.form[section][key], onChange: (event) => set(section, key, event.target.checked, ui) });
  return h("label", { class: "checkbox" }, input, h("span", { class: "box" }, icon("check")),
    h("span", { class: "check-text" }, h("b", {}, title), h("span", {}, sub)));
}

function sliderRow(ui, section, key, label, min, max, step, fmt) {
  const start = Number(mem.form[section][key] ?? min);
  const box = h("span", { class: "slider-value" }, fmt(start));
  const input = h("input", { type: "range", class: "slider", min, max, step, value: start, "aria-label": label, id: `aj-${section}-${key}` });
  const paint = () => input.style.setProperty("--pct", `${((Number(input.value) - min) / (max - min)) * 100}%`);
  input.addEventListener("input", () => {
    const value = step < 1 ? Math.round(Number(input.value) * 100) / 100 : Number(input.value);
    set(section, key, value, ui);
    box.textContent = fmt(value);
    paint();
  });
  paint();
  return h("div", { class: "srow" }, h("label", { class: "srow-label", for: `aj-${section}-${key}` }, label),
    h("div", { class: "slider-row" }, input, box),
    h("div", { class: "slider-bounds" }, h("span", {}, fmt(min)), h("span", {}, fmt(max))));
}

function initial(name) {
  const trimmed = (name || "").trim();
  return trimmed ? trimmed[0].toUpperCase() : "?";
}

function fmtSubs(value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  const short = n >= 1_000_000 ? `${(n / 1_000_000).toFixed(1)} mi` : n >= 1000 ? `${(n / 1000).toFixed(1)} mil` : String(n);
  return `${short} inscritos`;
}

/* ---------- actions ---------- */

async function testConnection(ui, btn) {
  btn.disabled = true;
  try {
    const body = { model: mem.form.ai.model || undefined };
    if (mem.apiKey.trim()) body.api_key = mem.apiKey.trim();
    const result = await api.post("/api/settings/test-connection", body);
    mem.data.ai.connection = result;
    if (result.ok) toast.success(result.message || "Conexão bem-sucedida!"); else toast.error(result.message || "Falha na conexão");
  } catch (err) {
    toast.error(err.message);
  } finally {
    btn.disabled = false;
    if (ui.alive) draw(ui);
  }
}

async function saveAll(ui) {
  const payload = diff();
  if (!Object.keys(payload).length) return;
  ui.saveBtn.disabled = true;
  try {
    const result = await api.put("/api/settings", payload);
    absorb(result.settings, { reset: true });
    toast.success("Alterações salvas.");
    if (ui.alive) draw(ui);
  } catch (err) {
    toast.error(err.message);
    updateSave(ui);
  }
}

async function restoreDefaults(ui) {
  const ok = await confirmDialog({
    title: "Restaurar padrões?", danger: true, confirmLabel: "Restaurar", icon: "rotate-ccw",
    body: "Publicação, marca, regras e pastas voltam aos valores originais do sistema. A chave da API e a conta do YouTube são mantidas.",
  });
  if (!ok) return;
  try {
    const result = await api.post("/api/settings/restore");
    absorb(result.settings, { reset: true });
    toast.success("Padrões restaurados.");
    if (ui.alive) draw(ui);
  } catch (err) {
    toast.error(err.message);
  }
}

async function disconnectYoutube(ui) {
  const ok = await confirmDialog({
    title: "Desconectar o YouTube?", danger: true, confirmLabel: "Desconectar", icon: "unplug",
    body: "O token de acesso será apagado deste computador e as publicações automáticas param até você reconectar a conta.",
  });
  if (!ok) return;
  try {
    const result = await api.post("/api/settings/youtube/disconnect");
    absorb(result.settings);
    toast.success("Conta do YouTube desconectada.");
    if (ui.alive) draw(ui);
  } catch (err) {
    toast.error(err.message);
  }
}

async function connectYoutube() {
  try {
    await api.post("/api/settings/youtube/connect");
    toast.info("A janela de autorização do Google abre neste computador. Conclua o login e volte aqui.");
  } catch (err) {
    toast.error(err.message);
  }
}
