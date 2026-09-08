// Biblioteca: filtros, quatro StatCards, grade de vídeos e painel de detalhe (/biblioteca e /biblioteca/:id).
import { h, icon, on } from "../dom.js";
import { api } from "../api.js";
import { router } from "../router.js";
import { sse } from "../sse.js";
import { fmtViews, fmtInt, fmtPct } from "../format.js";
import { PageHeader } from "../components/header.js";
import { Button, IconCircle, Ring, MiniBars, Thumb, setContent } from "../components/ui.js";
import { EmptyState, Skeleton } from "../components/states.js";
import { toast, confirmDialog } from "../components/feedback.js";

const STATES = [["", "Todos os estados"], ["published", "Publicado"], ["in_production", "Em produção"], ["failed", "Falha"], ["draft", "Rascunho"]];
const SORTS = [["recent", "Mais recentes"], ["oldest", "Mais antigos"], ["views", "Mais views"], ["retention", "Maior retenção"]];
const STATUS_PILL = {
  published: { cls: "green", icon: "circle-play", label: "Publicado" },
  in_production: { cls: "amber", icon: "clock", label: "Em produção" },
  failed: { cls: "red", icon: "circle-x", label: "Falha" },
  draft: { cls: "grey", icon: "file-text", label: "Rascunho" },
};
const STAT_CARDS = [
  ["published", "Publicados", "play", "green"],
  ["in_production", "Em produção", "clock", "amber"],
  ["drafts", "Rascunhos", "file-text", "blue"],
  ["avg_retention", "Média de retenção", "eye", "purple"],
];

// The seeded demo intentionally includes productions without a rendered video.
// Their local reference art avoids predictable /api/thumbs 404s while keeping
// the real thumbnail endpoint as the source for every non-demo production.
const DEMO_THUMBS = {
  "OMS-20260908-0001": "splash.jpg",
  "OMS-20260907-0002": "headphones.jpg",
  "OMS-20260907-0001": "globe.jpg",
  "OMS-20260906-0001": "eye.jpg",
  "OMS-20260905-0001": "coffee.jpg",
  "OMS-20260904-0001": "brain.jpg",
  "OMS-20260903-0001": "city.jpg",
  "OMS-20260901-0001": "hourglass.jpg",
  "OMS-20260827-0001": "brain.jpg",
  "OMS-20260825-0001": "city.jpg",
  "OMS-20260823-0001": "hourglass.jpg",
  "OMS-20260821-0001": "moon.jpg",
  "OMS-20260820-0001": "moon.jpg",
  "OMS-20260819-0001": "ice.jpg",
  "OMS-20260818-0001": "glass.jpg",
  "OMS-20260817-0001": "eye.jpg",
  "OMS-20260816-0001": "mountains.jpg",
  "OMS-20260815-0001": "eye-clean.jpg",
  "OMS-20260814-0001": "glass.jpg",
  "OMS-20260813-0001": "ice.jpg",
  "OMS-20260812-0001": "mountains.jpg",
  "OMS-20260810-0001": "coffee-small.jpg",
  "OMS-20260808-0001": "logo-thumb.jpg",
  "OMS-20260806-0001": "moon.jpg",
};

// Filtros e último payload sobrevivem a re-renderizações (voltar/avançar do navegador, SSE).
const filters = { q: "", state: "", category: "", sort: "recent" };
let cache = null; // { key, data }

function eagerThumb(url, options) {
  const thumb = Thumb(url, options);
  const image = thumb.querySelector("img");
  if (image) image.loading = "eager";
  return thumb;
}

function productionPath(screen, id) {
  return `/${screen}/${encodeURIComponent(String(id || ""))}`;
}

function thumbnailFor(item) {
  const demo = DEMO_THUMBS[item?.id];
  return demo ? `/static/img/demo/${demo}` : item?.thumb_url;
}

function filterKey() {
  return new URLSearchParams(filters).toString();
}

function hasFilters() {
  return Boolean(filters.q || filters.state || filters.category || filters.sort !== "recent");
}

function retentionTone(pct) {
  if (pct === null || pct === undefined) return "grey";
  if (pct < 40) return "red";
  if (pct < 60) return "amber";
  return "green";
}

export async function render(container, params) {
  container.append(PageHeader("Biblioteca", "Todos os seus vídeos publicados e rascunhos em um só lugar."));
  const root = h("div", { class: "scr-biblioteca" });
  container.append(root);

  let data = null;
  let selectedId = params?.id || null;
  // The reference opens the library with a useful, published video in focus.
  // Keep that one-time default separate from an explicit close/filter action.
  let initialSelectionPending = !selectedId;
  let disposed = false;
  let debounce = null;
  let openMenu = null;

  const statsEl = h("div", { class: "lib-stats" });
  const gridEl = h("div", { class: "lib-grid" });
  const panelEl = h("aside", { class: "lib-panel hidden", "aria-label": "Detalhe do vídeo" });
  const bodyEl = h("div", { class: "lib-body" }, gridEl, panelEl);

  // ---------- filtros ----------
  const searchInput = h("input", { class: "input lib-search-input", type: "search", placeholder: "Buscar vídeo...", value: filters.q,
    "aria-label": "Buscar vídeo", autocomplete: "off",
    onInput: () => { clearTimeout(debounce); debounce = setTimeout(() => { filters.q = searchInput.value.trim(); load(); }, 250); } });
  const stateSelect = selectField("Filtrar por estado", STATES, filters.state, (v) => { filters.state = v; load(); });
  const categorySelect = selectField("Filtrar por categoria", [["", "Todas as categorias"]], filters.category, (v) => { filters.category = v; load(); });
  const sortSelect = selectField("Ordenar", SORTS, filters.sort, (v) => { filters.sort = v; load(); }, "arrow-up-down");
  const newButton = Button({ label: "Novo vídeo", icon: "plus", cls: "lib-new", onClick: () => createProduction(newButton) });
  const filtersEl = h("div", { class: "lib-filters" },
    h("div", { class: "input-wrap has-icon lib-search" }, icon("search"), searchInput),
    stateSelect.wrap, categorySelect.wrap, sortSelect.wrap, newButton);

  root.append(filtersEl, statsEl, bodyEl);

  function selectField(label, options, value, onChange, leadIcon = null) {
    const select = h("select", { class: "select", "aria-label": label, onChange: () => onChange(select.value) });
    fillOptions(select, options, value);
    const wrap = h("div", { class: `select-wrap lib-select ${leadIcon ? "has-lead" : ""}`.trim() },
      leadIcon ? icon(leadIcon, "lead") : null, select, icon("chevron-down"));
    return { wrap, select };
  }

  function fillOptions(select, options, value) {
    setContent(select, options.map(([v, label]) => h("option", { value: v, selected: v === value }, label)));
    select.value = value;
  }

  // ---------- carregamento ----------
  function renderSkeleton() {
    setContent(statsEl, STAT_CARDS.map(() => h("section", { class: "card lib-stat lib-stat-skel" },
      Skeleton({ height: 52, width: 52, cls: "round" }), h("div", { class: "lib-stat-text" }, Skeleton({ height: 26, width: "40%" }), Skeleton({ height: 14, width: "70%" })))));
    setContent(gridEl, Array.from({ length: 8 }, () => h("article", { class: "card lib-card lib-card-skel" },
      Skeleton({ height: "auto", cls: "lib-skel-thumb" }),
      h("div", { class: "lib-card-body" }, Skeleton({ height: 14, width: "85%" }), Skeleton({ height: 14, width: "55%" }),
        Skeleton({ height: 24, width: 96, cls: "pill-skel" }), Skeleton({ height: 12, width: "60%" }), Skeleton({ height: 14, width: "75%" }), Skeleton({ height: 22, width: 64, cls: "pill-skel" })))));
  }

  async function load({ silent = false } = {}) {
    const key = filterKey();
    if (!silent && !(cache && cache.key === key)) renderSkeleton();
    else if (cache && cache.key === key && !data) { data = cache.data; draw(); }
    try {
      const fresh = await api.get(`/api/productions?${key}`);
      if (disposed || key !== filterKey()) return;
      data = fresh;
      cache = { key, data: fresh };
      draw();
    } catch (err) {
      if (disposed) return;
      toast.error(err.message || "Não foi possível carregar a biblioteca.");
      if (!data) {
        setContent(statsEl);
        setContent(gridEl, EmptyState({ icon: "circle-alert", title: "Algo deu errado", text: err.message || String(err),
          action: Button({ label: "Tentar de novo", icon: "refresh-cw", onClick: () => load() }) }));
      }
    }
  }

  // ---------- desenho ----------
  function draw() {
    const items = data.items || [];
    if (initialSelectionPending && !selectedId && items.length) {
      selectedId = (items.find((item) => item.status === "published") || items[0]).id;
      initialSelectionPending = false;
    }
    drawStats(data.stats || {});
    const cats = [["", "Todas as categorias"], ...(data.categories || []).map((c) => [c, c])];
    if (filters.category && !(data.categories || []).includes(filters.category)) cats.push([filters.category, filters.category]);
    fillOptions(categorySelect.select, cats, filters.category);
    drawGrid(items);
    if (selectedId && !items.some((i) => i.id === selectedId)) {
      // O item selecionado pode estar fora do filtro atual: busca só o detalhe.
      drawPanel(null);
      fetchSelected(selectedId);
    } else {
      drawPanel(items.find((i) => i.id === selectedId) || null);
    }
  }

  async function fetchSelected(id) {
    try {
      const r = await api.get(`/api/productions?q=${encodeURIComponent(id)}`);
      if (disposed || selectedId !== id) return;
      const item = (r.items || []).find((i) => i.id === id) || null;
      if (item) drawPanel(item);
      else { selectedId = null; syncUrl(); drawPanel(null); toast.error("Vídeo não encontrado."); }
    } catch (err) {
      if (!disposed && selectedId === id) toast.error(err.message || "Não foi possível carregar o vídeo selecionado.");
    }
  }

  function drawStats(stats) {
    setContent(statsEl, STAT_CARDS.map(([key, label, iconName, color]) => {
      const s = stats[key] || {};
      const value = s.value === null || s.value === undefined ? "—" : key === "avg_retention" ? fmtPct(s.value) : fmtInt(s.value);
      return h("section", { class: "card lib-stat" },
        IconCircle(iconName, color, "lg"),
        h("div", { class: "lib-stat-text" }, h("b", { class: "lib-stat-num" }, value), h("span", { class: "lib-stat-label" }, label)),
        h("div", { class: "lib-stat-side" }, StatDelta(s.delta), MiniBars(s.series || [])));
    }));
  }

  function StatDelta(value) {
    if (value === null || value === undefined) return h("span", { class: "lib-delta flat" }, "—");
    const n = Number(value);
    const tone = n > 0 ? "up" : n < 0 ? "down" : "zero";
    return h("span", { class: `lib-delta ${tone}` }, `${n > 0 ? "+" : ""}${n}%`);
  }

  function drawGrid(items) {
    closeMenu();
    if (!items.length) {
      const empty = hasFilters()
        ? EmptyState({ icon: "search", title: "Nada encontrado", text: "Nenhum vídeo combina com a busca e os filtros atuais.",
          action: Button({ label: "Limpar filtros", icon: "x", variant: "secondary", onClick: clearFilters }) })
        : EmptyState({ icon: "folder-open", title: "Nenhum vídeo ainda", text: "Crie a primeira produção e ela aparece aqui com miniatura, status e desempenho.",
          action: Button({ label: "Novo vídeo", icon: "plus", onClick: () => createProduction() }) });
      setContent(gridEl, h("div", { class: "lib-empty" }, empty));
      return;
    }
    setContent(gridEl, items.map(VideoCard));
  }

  function VideoCard(item) {
    const status = STATUS_PILL[item.status] || STATUS_PILL.draft;
    const card = h("article", { class: `card lib-card ${item.id === selectedId ? "selected" : ""}`.trim(), dataset: { id: item.id }, tabindex: 0,
      role: "button", "aria-label": item.title, "aria-pressed": item.id === selectedId ? "true" : "false",
      onClick: () => select(item.id),
      onKeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(item.id); } } });
    const thumb = eagerThumb(thumbnailFor(item), { orientation: "v", cls: "lib-thumb", alt: "" });
    thumb.append(h("span", { class: "lib-duration" }, item.duration || "--:--"), Kebab(item, "on-thumb"));
    card.append(thumb,
      h("div", { class: "lib-card-body" },
        h("div", { class: "lib-card-title-row" }, h("h3", { class: "lib-card-title" }, item.title), Kebab(item, "on-title")),
        StatusPill(status, item.status_label || status.label),
        h("span", { class: "lib-card-date" }, item.date_label || "—"),
        h("div", { class: "lib-card-metrics" },
          h("span", { class: "lib-metric" }, icon("eye"), h("b", {}, fmtViews(item.views))),
          h("span", { class: "lib-metric" }, Ring(item.retention, { size: 18, stroke: 3, color: retentionTone(item.retention) }), h("b", {}, item.retention === null || item.retention === undefined ? "—" : fmtPct(item.retention)))),
        h("span", { class: "pill pill-dark pill-sm lib-tag" }, item.category || "—")));
    return card;
  }

  function StatusPill(status, label) {
    return h("span", { class: `pill lib-pill ${status.cls}` }, h("span", { class: "lib-pill-ic" }, icon(status.icon)), label);
  }

  function Kebab(item, cls) {
    return h("button", { class: `lib-kebab ${cls}`, type: "button", "aria-label": `Ações de ${item.title}`, "aria-haspopup": "menu",
      onClick: (e) => { e.stopPropagation(); toggleMenu(e.currentTarget, item); },
      onKeydown: (e) => e.stopPropagation() }, icon("ellipsis-vertical"));
  }

  function toggleMenu(anchor, item) {
    if (openMenu && openMenu.anchor === anchor) { closeMenu(); return; }
    closeMenu();
    const menu = h("div", { class: "lib-menu", role: "menu", onClick: (e) => e.stopPropagation(), onKeydown: (e) => e.stopPropagation() },
      MenuItem("clapperboard", "Abrir no Estúdio", () => router.navigate(productionPath("estudio", item.id))),
      item.status === "published" ? MenuItem("chart-column-big", "Abrir desempenho", () => router.navigate(productionPath("desempenho", item.id))) : null,
      MenuItem("copy", "Duplicar fluxo", () => duplicate(item)),
      MenuItem("trash", "Apagar", () => remove(item), "danger"));
    const card = anchor.closest(".lib-card");
    card.append(menu);
    menu.style.top = `${anchor.offsetTop + anchor.offsetHeight + 4}px`;
    anchor.setAttribute("aria-expanded", "true");
    openMenu = { anchor, menu };
    menu.querySelector("button")?.focus();
  }

  function MenuItem(iconName, label, action, cls = "") {
    return h("button", { class: `lib-menu-item ${cls}`.trim(), type: "button", role: "menuitem", onClick: () => { closeMenu(); action(); } }, icon(iconName), label);
  }

  function closeMenu() {
    if (!openMenu) return;
    openMenu.menu.remove();
    openMenu.anchor.removeAttribute("aria-expanded");
    openMenu = null;
  }

  function drawPanel(item) {
    root.classList.toggle("has-panel", Boolean(item));
    panelEl.classList.toggle("hidden", !item);
    gridEl.querySelectorAll(".lib-card").forEach((el) => {
      const sel = Boolean(item) && el.dataset.id === item.id;
      el.classList.toggle("selected", sel);
      el.setAttribute("aria-pressed", sel ? "true" : "false");
    });
    if (!item) { setContent(panelEl); return; }
    const published = item.status === "published";
    const thumb = eagerThumb(thumbnailFor(item), { orientation: "h", cls: "lib-panel-thumb", alt: "" });
    thumb.append(h("span", { class: "lib-duration" }, item.duration || "--:--"));
    const primary = published
      ? Button({ label: "Abrir desempenho", icon: "chart-column-big", trailing: "chevron-right", cls: "lib-panel-btn", href: productionPath("desempenho", item.id) })
      : Button({ label: "Abrir no Estúdio", icon: "clapperboard", trailing: "chevron-right", cls: "lib-panel-btn", href: productionPath("estudio", item.id) });
    setContent(panelEl, h("section", { class: "card lib-panel-card" },
      h("button", { class: "lib-close", type: "button", "aria-label": "Fechar painel", onClick: () => select(null) }, icon("x")),
      thumb,
      h("h2", { class: "lib-panel-title" }, item.title),
      h("span", { class: "lib-panel-id" }, item.id),
      h("p", { class: "lib-panel-desc" }, item.description || "—"),
      h("ul", { class: "lib-meta" },
        MetaRow(icon("calendar", "red"), "Publicado em", item.published_label || "—"),
        MetaRow(icon("eye"), "Visualizações", fmtInt(item.views)),
        MetaRow(Ring(item.retention, { size: 26, stroke: 3.5, color: retentionTone(item.retention) }), "Retenção média", item.retention === null || item.retention === undefined ? "—" : fmtPct(item.retention)),
        MetaRow(icon("heart"), "Curtidas", fmtViews(item.likes)),
        MetaRow(icon("tag"), "Categoria", item.category || "—")),
      primary,
      Button({ label: "Duplicar fluxo", icon: "copy", variant: "secondary", cls: "lib-panel-btn", onClick: () => duplicate(item) })));
  }

  function MetaRow(iconEl, label, value) {
    return h("li", { class: "lib-meta-row" }, h("span", { class: "lib-meta-ic" }, iconEl), h("div", {}, h("span", { class: "lib-meta-label" }, label), h("b", { class: "lib-meta-value" }, value)));
  }

  // ---------- seleção e URL ----------
  function select(id) {
    closeMenu();
    initialSelectionPending = false;
    selectedId = id;
    syncUrl();
    const item = (data?.items || []).find((i) => i.id === selectedId) || null;
    drawPanel(item);
    if (selectedId && !item) fetchSelected(selectedId);
  }

  function syncUrl() {
    // replaceState em vez de router.navigate: o router sempre re-renderiza a tela inteira ao navegar.
    const path = selectedId ? `/biblioteca/${encodeURIComponent(selectedId)}` : "/biblioteca";
    if (location.pathname !== path) history.replaceState({}, "", path);
    router.current = { ...router.current, path, params: selectedId ? { id: selectedId } : {}, pattern: selectedId ? "/biblioteca/:id" : "/biblioteca" };
  }

  function clearFilters() {
    Object.assign(filters, { q: "", state: "", category: "", sort: "recent" });
    searchInput.value = "";
    stateSelect.select.value = "";
    sortSelect.select.value = "recent";
    load();
  }

  // ---------- ações ----------
  async function createProduction(button = null) {
    if (button) button.disabled = true;
    try {
      let result;
      try {
        result = await api.post("/api/productions", { force: false });
      } catch (err) {
        if (err.status !== 409) throw err;
        const ok = await confirmDialog({ title: "Limite diário atingido", body: "Criar outra produção hoje mesmo assim?", confirmLabel: "Criar mesmo assim", icon: "plus" });
        if (!ok) return;
        result = await api.post("/api/productions", { force: true });
      }
      toast.success("Produção criada.");
      router.navigate(productionPath("estudio", result.id));
    } catch (err) {
      toast.error(err.message || "Não foi possível criar a produção.");
    } finally {
      if (button) button.disabled = false;
    }
  }

  async function duplicate(item) {
    const ok = await confirmDialog({ title: "Duplicar fluxo", body: `Cria uma nova produção a partir de "${item.title}", com o mesmo tema e as mesmas configurações.`, confirmLabel: "Duplicar", icon: "copy" });
    if (!ok) return;
    try {
      const result = await api.post(`/api/productions/${encodeURIComponent(item.id)}/duplicate`);
      toast.success("Fluxo duplicado.");
      router.navigate(productionPath("estudio", result.id));
    } catch (err) {
      toast.error(err.message || "Não foi possível duplicar.");
    }
  }

  async function remove(item) {
    const ok = await confirmDialog({ title: "Apagar vídeo?", body: `"${item.title}" e todos os seus arquivos serão removidos. Isso não pode ser desfeito.`, confirmLabel: "Apagar", danger: true, icon: "trash" });
    if (!ok) return;
    try {
      await api.del(`/api/productions/${encodeURIComponent(item.id)}`);
      toast.success("Vídeo apagado.");
      if (selectedId === item.id) { selectedId = null; syncUrl(); drawPanel(null); }
      await load({ silent: true });
    } catch (err) {
      toast.error(err.message || "Não foi possível apagar.");
    }
  }

  // ---------- eventos globais ----------
  const offDoc = on(document, "click", () => closeMenu());
  const offKey = on(document, "keydown", (e) => { if (e.key === "Escape") { if (openMenu) closeMenu(); else if (selectedId) select(null); } });
  const offSse = sse.on("state", () => load({ silent: true }));

  await load();

  return () => {
    disposed = true;
    clearTimeout(debounce);
    closeMenu();
    offDoc(); offKey(); offSse();
  };
}
