// Conversa: chat with the assistant (tools over the Orchestrator), quick commands, recent actions and capabilities.
import { h, icon, on } from "../dom.js";
import { api } from "../api.js";
import { router } from "../router.js";
import { sse } from "../sse.js";
import { state } from "../state.js";
import { PageHeader } from "../components/header.js";
import { Card, Pill, Button, LinkAction, setContent } from "../components/ui.js";
import { EmptyState, Skeleton, Progress } from "../components/states.js";
import { toast, confirmDialog } from "../components/feedback.js";

const AVATAR = "/static/img/avatar-assistente.png";
const NOTE = "/static/img/note-conversa.png";
const ICON_ALIASES = { "bar-chart-3": "chart-no-axes-column-increasing", "chart-column-big": "chart-no-axes-column-increasing", "bar-chart": "chart-column" };
const JOB_LABELS = { prepare: "roteiro e prompts prontos", finish: "vídeo final montado", collect: "clipes validados e vídeo montado", publish: "publicado no YouTube", resume: "produção avançou", reset: "tema e roteiro refeitos", analytics: "métricas coletadas", learn: "aprendizado atualizado" };

// Demo history is intentionally retained after the generated media expires.
// These local assets prevent the visible theme cards from degrading to a blank box.
const DEMO_CARD_THUMBS = {
  "OMS-20260908-0001": "hourglass.jpg",
  "OMS-20260907-0002": "eye.jpg",
  "OMS-20260907-0001": "globe.jpg",
};

const iconName = (name) => ICON_ALIASES[name] || name || "sparkles";
const clockNow = () => new Date().toTimeString().slice(0, 5);

function safeAppHref(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value.trim(), window.location.origin);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/")) return null;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return null;
  }
}

function cardThumbnail(card) {
  const demo = DEMO_CARD_THUMBS[card?.production_id];
  return demo ? `/static/img/demo/${demo}` : card?.thumb_url;
}

export async function render(container) {
  container.append(PageHeader("Conversa", "Controle todo o sistema em linguagem natural. Fale com o seu assistente."));
  const root = h("div", { class: "scr-conversa" });
  container.append(root);

  // ------------------------------------------------------------------ chat card
  const list = h("div", { class: "cv-list", role: "log", "aria-live": "polite", "aria-label": "Mensagens" });
  const input = h("input", { class: "cv-input", type: "text", placeholder: "Escreva uma mensagem...", autocomplete: "off", "aria-label": "Mensagem para o assistente", maxlength: "2000" });
  const sendBtn = Button({ icon: "send", variant: "primary", cls: "btn-circle cv-send", type: "submit", title: "Enviar" });
  sendBtn.setAttribute("aria-label", "Enviar mensagem");
  const attach = h("button", { class: "cv-attach", type: "button", title: "Enviar clipes", "aria-label": "Enviar clipes", onClick: () => router.navigate("/estudio?step=3") }, icon("paperclip"));
  const form = h("form", { class: "cv-compose", onSubmit: (event) => { event.preventDefault(); submit(); } },
    h("div", { class: "cv-field" }, attach, input,
      h("span", { class: "cv-hint" }, h("b", {}, "Ctrl + Enter"), " para enviar")),
    sendBtn);
  const chat = h("section", { class: "card cv-chat" },
    h("div", { class: "cv-head" },
      h("span", { class: "cv-avatar lg" }, h("img", { src: AVATAR, alt: "" })),
      h("div", { class: "cv-head-text" },
        h("div", { class: "cv-head-row" }, h("h2", { class: "cv-name" }, "Assistente OneMoreShort"), h("span", { class: "pill pill-green-soft cv-online" }, h("span", { class: "cv-online-dot" }), "online")),
        h("p", { class: "cv-head-sub" }, "Seu assistente de criação de vídeos curtos")),
      h("img", { class: "cv-note", src: NOTE, alt: "", width: 142, height: 86 })),
    list, form);

  // ------------------------------------------------------------------ side column
  const quickBody = h("div", { class: "cv-quick-grid" });
  const activityBody = h("div", { class: "cv-timeline" });
  const capsBody = h("div", { class: "cv-caps-grid" });
  const side = h("aside", { class: "cv-side" },
    Card({ icon: "zap", title: "Comandos rápidos", subtitle: "Ações que você pode pedir para o assistente.", cls: "cv-card-quick",
      action: LinkAction("Ver todos", { onClick: () => { quickBody.scrollIntoView({ behavior: "smooth", block: "nearest" }); quickBody.querySelector("button")?.focus(); } }), body: quickBody }),
    Card({ icon: "history", title: "Ações recentes", subtitle: "Últimas operações realizadas via conversa.", cls: "cv-card-activity",
      action: LinkAction("Ver todas", { href: "/biblioteca" }), body: activityBody }),
    Card({ icon: "sparkles", title: "O que o assistente faz", subtitle: "Seu parceiro completo na criação de vídeos.", cls: "cv-card-caps", body: capsBody }));
  root.append(chat, side);

  // skeletons while the history loads
  setContent(list, h("div", { class: "cv-skel" }, Skeleton({ height: 40, width: "42%", cls: "right" }), Skeleton({ height: 170, width: "68%" }), Skeleton({ height: 40, width: "36%", cls: "right" }), Skeleton({ height: 170, width: "68%" })));
  setContent(quickBody, ...Array.from({ length: 5 }, () => Skeleton({ height: 56 })));
  setContent(activityBody, ...Array.from({ length: 5 }, () => Skeleton({ height: 34 })));
  setContent(capsBody, ...Array.from({ length: 4 }, () => Skeleton({ height: 77 })));

  // ------------------------------------------------------------------ state
  const jobCards = new Map(); // job id -> { progress, status }
  let busy = false;
  let typing = null;

  function scrollToEnd() { list.scrollTop = list.scrollHeight; }

  function appendMessage(msg) {
    list.querySelector(".cv-empty")?.remove();
    list.append(msg.role === "user" ? UserMessage(msg) : AssistantMessage(msg, { onSend: sendMessage, jobCards }));
    scrollToEnd();
  }

  function appendAssistantText(text) { appendMessage({ role: "assistant", text, cards: [], time: clockNow() }); }

  function setBusy(value) {
    busy = value;
    sendBtn.disabled = value;
    if (value) {
      typing = h("div", { class: "cv-msg assistant cv-typing", "aria-label": "O assistente está escrevendo" },
        h("div", { class: "cv-asst-col" }, h("span", { class: "cv-avatar" }, h("img", { src: AVATAR, alt: "" }))),
        h("div", { class: "cv-bubble cv-dots" }, h("span"), h("span"), h("span")));
      list.append(typing);
      scrollToEnd();
    } else {
      typing?.remove();
      typing = null;
    }
  }

  async function refreshActivity() {
    try {
      const data = await api.get("/api/chat/history");
      renderActivity(activityBody, data.activity || []);
    } catch { /* keep the previous list */ }
  }

  async function handleConfirm(confirm) {
    if (!confirm || !confirm.production_id) return;
    const isDelete = confirm.kind === "delete";
    const ok = await confirmDialog({ title: confirm.title || (isDelete ? "Apagar esta produção?" : "Publicar no YouTube?"), body: confirm.body || "",
      confirmLabel: isDelete ? "Apagar" : "Publicar", danger: isDelete, icon: isDelete ? "trash" : "upload" });
    if (!ok) { appendAssistantText(isDelete ? "Tudo bem, nada foi apagado." : "Tudo bem, a publicação não foi feita."); return; }
    try {
      if (isDelete) {
        await api.del(`/api/productions/${encodeURIComponent(confirm.production_id)}`);
        toast.success("Produção apagada.");
        appendAssistantText("Produção apagada.");
      } else {
        const result = await api.post(`/api/productions/${encodeURIComponent(confirm.production_id)}/publish`, { confirm: true });
        toast.success("Publicação iniciada.");
        appendMessage({ role: "assistant", text: "Publicando… aviso aqui quando o vídeo estiver no ar.", time: clockNow(),
          cards: result?.job ? [{ kind: "job", title: "Publicando no YouTube", job: result.job, production_id: confirm.production_id,
            buttons: [{ label: "Acompanhar no Estúdio", href: `/estudio/${confirm.production_id}?step=5`, icon: "clapperboard" }] }] : [] });
      }
    } catch (err) {
      toast.error(err.message || "Não foi possível concluir a ação.");
    }
    refreshActivity();
  }

  async function sendMessage(text) {
    const message = String(text || "").trim();
    if (!message || busy) return;
    appendMessage({ role: "user", text: message, cards: [], time: clockNow() });
    setBusy(true);
    try {
      const reply = await api.post("/api/chat", { message });
      setBusy(false);
      appendMessage({ role: "assistant", text: reply.text || "", cards: reply.cards || [], actions: reply.actions || [], time: reply.time || clockNow() });
      if (reply.confirm) await handleConfirm(reply.confirm);
      refreshActivity();
    } catch (err) {
      setBusy(false);
      toast.error(err.message || "Falha de rede ao falar com o assistente.");
      if (!input.value) input.value = message;
    }
    input.focus();
  }

  function submit() {
    const value = input.value;
    if (!value.trim() || busy) return;
    input.value = "";
    sendMessage(value);
  }

  const offKey = on(input, "keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); }
  });

  // ------------------------------------------------------------------ live updates for jobs started from the chat
  const offJob = sse.on("job", (job) => {
    if (!job || !jobCards.has(job.id)) return;
    const entry = jobCards.get(job.id);
    updateJobCard(entry, job);
    if (job.status === "done" && entry.status !== "done") {
      entry.status = "done";
      appendAssistantText(`Pronto: ${JOB_LABELS[job.name] || job.name}.`);
      refreshActivity();
    } else if ((job.status === "failed" || job.status === "human_action") && entry.status !== job.status) {
      entry.status = job.status;
      appendAssistantText(job.status === "failed" ? `Falhou: ${job.error || job.name}. Veja os detalhes na tela Hoje.` : `Preciso de você: ${job.error || "ação humana necessária"}. Veja a tela Hoje.`);
      refreshActivity();
    }
  });

  // ------------------------------------------------------------------ load
  try {
    const data = await api.get("/api/chat/history");
    renderQuick(quickBody, data.quick_commands || [], sendMessage);
    renderActivity(activityBody, data.activity || []);
    renderCaps(capsBody, data.capabilities || []);
    setContent(list);
    const messages = data.messages || [];
    if (!messages.length) {
      list.append(h("div", { class: "cv-empty" }, EmptyState({ icon: "message-circle", title: "Comece uma conversa",
        text: "Peça para começar o vídeo de hoje, trocar o tema ou ver como foi o último vídeo.",
        action: Button({ label: "Começar o dia", icon: "play", size: "btn-sm", onClick: () => sendMessage("começa o vídeo de hoje") }) })));
    } else {
      // Keep the beginning of the saved conversation visible on entry. New
      // messages still scroll to the end in appendMessage(), but opening the
      // page should match the chronological reading order of the reference.
      messages.forEach((m) => list.append(m.role === "user" ? UserMessage(m) : AssistantMessage(m, { onSend: sendMessage, jobCards })));
    }
  } catch (err) {
    toast.error(err.message || "Não foi possível carregar a conversa.");
    setContent(list, h("div", { class: "cv-empty" }, EmptyState({ icon: "circle-alert", title: "Não foi possível carregar a conversa", text: err.message || "",
      action: Button({ label: "Tentar de novo", icon: "refresh-cw", size: "btn-sm", onClick: () => router.navigate("/conversa", { replace: true }) }) })));
    setContent(quickBody); setContent(activityBody); setContent(capsBody);
  }

  return () => { offJob(); offKey(); };
}

// ====================================================================== messages
function UserMessage(msg) {
  return h("div", { class: "cv-msg user" },
    h("span", { class: "cv-time" }, msg.time || ""),
    h("div", { class: "cv-bubble user" }, msg.text || ""),
    h("span", { class: "cv-user-avatar", "aria-hidden": "true" }, icon("user")));
}

function AssistantMessage(msg, { onSend, jobCards }) {
  const cards = (msg.cards || []).map((card) => RichCard(card, { jobCards }));
  const actions = (msg.actions || []).filter((a) => a && a.label && (!a.href || safeAppHref(a.href) || a.message));
  return h("div", { class: "cv-msg assistant" },
    h("div", { class: "cv-asst-col" }, h("span", { class: "cv-avatar" }, h("img", { src: AVATAR, alt: "" })), h("span", { class: "cv-time" }, msg.time || "")),
    h("div", { class: "cv-bubble" },
      msg.text ? h("p", { class: "cv-text" }, msg.text) : null,
      ...cards,
      actions.length ? h("div", { class: "cv-actions" }, ...actions.map((a) => safeAppHref(a.href)
        ? Button({ label: a.label, variant: "secondary", size: "btn-sm", href: safeAppHref(a.href), trailing: "chevron-right" })
        : Button({ label: a.label, variant: "secondary", size: "btn-sm", onClick: () => onSend(a.message || a.label) }))) : null));
}

function cardButtons(card) {
  const buttons = (card.buttons || []).filter((b) => b && b.label && (!b.href || safeAppHref(b.href)));
  if (!buttons.length) return null;
  return h("div", { class: "cv-card-btns" }, ...buttons.map((b, i) => Button({
    label: b.label, icon: b.icon ? iconName(b.icon) : null, variant: "secondary", size: "btn-sm", href: safeAppHref(b.href),
    trailing: b.trailing || i === buttons.length - 1 ? "chevron-right" : null })));
}

function cardPills(card) {
  const pills = (card.pills || []).filter((p) => p && p.label);
  return pills.length ? h("div", { class: "cv-card-pills" }, ...pills.map((p) => Pill(p.label, p.variant || "grey"))) : null;
}

function RichCard(card, { jobCards }) {
  const kind = card.kind || "theme";
  if (kind === "job") return JobCard(card, jobCards);
  if (kind === "list") {
    return h("div", { class: "cv-card list" },
      h("div", { class: "cv-card-body" },
        card.title ? h("h3", { class: "cv-card-title" }, card.title) : null,
        cardPills(card),
        (card.items || []).length ? h("ul", { class: "cv-card-list" }, ...card.items.map((item) => h("li", {}, icon("check", "ic-xs"), h("span", {}, String(item))))) : null,
        cardButtons(card)));
  }
  const horizontal = kind === "report";
  return h("div", { class: `cv-card ${kind}` },
    ThumbBox(cardThumbnail(card), horizontal ? "h" : "v", card.title || ""),
    h("div", { class: "cv-card-body" },
      card.title ? h("h3", { class: "cv-card-title" }, card.title) : null,
      cardPills(card),
      cardButtons(card)));
}

function ThumbBox(url, orientation, alt) {
  const wrap = h("div", { class: `cv-thumb ${orientation}` });
  const fallback = h("div", { class: "cv-thumb-fallback" }, icon("film"));
  wrap.append(fallback);
  if (url) {
    const img = h("img", { alt: "", loading: "eager" });
    img.addEventListener("load", () => fallback.remove());
    img.addEventListener("error", () => img.remove());
    img.src = url;
    wrap.append(img);
  }
  return wrap;
}

function JobCard(card, jobCards) {
  const job = card.job || null;
  const live = job && job.id === state.job?.id ? state.job : job;
  const running = live && (live.status === "running" || live.status === "queued");
  const progress = h("div", { class: "cv-job-progress" });
  const status = h("span", { class: "cv-job-status" });
  const entry = { progress, statusEl: status, status: live?.status || null };
  const el = h("div", { class: "cv-card job" },
    h("div", { class: "cv-card-body" },
      h("div", { class: "cv-job-head" }, icon("loader", "cv-job-icon"), h("h3", { class: "cv-card-title" }, card.title || "Trabalhando"), status),
      progress, cardButtons(card)));
  updateJobCard(entry, live || { status: running ? "running" : "done", stage_label: "" });
  if (job?.id) jobCards.set(job.id, entry);
  return el;
}

function updateJobCard(entry, job) {
  const running = job.status === "running" || job.status === "queued";
  setContent(entry.progress, running ? [Progress(null), job.stage_label ? h("span", { class: "cv-job-stage" }, job.stage_label) : null] : []);
  const label = { done: "Concluído", failed: "Falhou", human_action: "Precisa de você", running: "Em andamento", queued: "Na fila" }[job.status] || "";
  setContent(entry.statusEl, label ? Pill(label, job.status === "done" ? "green-soft" : job.status === "failed" || job.status === "human_action" ? "red" : "dark", { size: "pill-sm" }) : []);
  entry.progress.closest(".cv-card")?.classList.toggle("running", running);
}

// ====================================================================== side column
function renderQuick(body, commands, onSend) {
  setContent(body, ...commands.map((cmd) => h("button", { class: "cv-quick", type: "button", onClick: () => onSend(cmd.message || cmd.title) },
    icon(iconName(cmd.icon), "cv-quick-icon"),
    h("span", { class: "cv-quick-text" }, h("b", {}, cmd.title || ""), h("span", {}, cmd.text || "")))));
  if (!commands.length) body.append(h("p", { class: "cv-side-empty" }, "Nenhum comando disponível."));
}

function renderActivity(body, items) {
  if (!items.length) {
    setContent(body, EmptyState({ icon: "history", title: "Nada por aqui", text: "As operações feitas pela conversa aparecem aqui." }));
    return;
  }
  setContent(body, ...items.map((item, i) => h("div", { class: `cv-act tone-${item.color || "green"} ${i === items.length - 1 ? "last" : ""}`.trim() },
    h("span", { class: "cv-act-rail" }, h("span", { class: "cv-act-dot" }), h("span", { class: "cv-act-line" })),
    h("span", { class: "cv-act-time" }, item.day ? h("span", {}, item.day) : null, h("span", {}, item.time || "")),
    h("div", { class: "cv-act-text" }, h("b", {}, item.label || ""), item.subject ? h("span", {}, item.subject) : null))));
}

function renderCaps(body, caps) {
  setContent(body, ...caps.map((cap) => h("div", { class: "cv-cap" },
    icon(iconName(cap.icon), "cv-cap-icon"),
    h("div", { class: "cv-cap-text" }, h("b", {}, cap.title || ""), h("span", {}, cap.text || "")))));
}
