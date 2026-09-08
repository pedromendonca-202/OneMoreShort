// History-API router: register("/desempenho/:id", module) where module.render(container, params) returns a cleanup fn.
const routes = [];
let notFound = null;
let cleanup = null;
let listeners = [];

export const router = {
  current: { path: "/", params: {}, query: new URLSearchParams() },

  register(pattern, module) {
    const keys = [];
    const regex = new RegExp("^" + pattern.replace(/\/:([a-zA-Z]+)/g, (_, key) => { keys.push(key); return "/([^/]+)"; }) + "/?$");
    routes.push({ pattern, regex, keys, module });
  },

  setNotFound(module) { notFound = module; },

  navigate(path, { replace = false } = {}) {
    if (replace) history.replaceState({}, "", path);
    else history.pushState({}, "", path);
    router.resolve();
  },

  onChange(fn) { listeners.push(fn); return () => { listeners = listeners.filter((l) => l !== fn); }; },

  async resolve() {
    const url = new URL(location.href);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    let match = null;
    for (const route of routes) {
      const m = route.regex.exec(path);
      if (m) {
        const params = {};
        route.keys.forEach((key, i) => { params[key] = decodeURIComponent(m[i + 1]); });
        match = { route, params };
        break;
      }
    }
    router.current = { path, params: match ? match.params : {}, query: url.searchParams, pattern: match ? match.route.pattern : null };
    const module = match ? match.route.module : notFound;
    const main = document.getElementById("main");
    if (typeof cleanup === "function") { try { cleanup(); } catch { /* ignore */ } }
    cleanup = null;
    while (main.firstChild) main.removeChild(main.firstChild);
    main.scrollTop = 0;
    window.scrollTo(0, 0);
    listeners.forEach((fn) => fn(router.current));
    try {
      cleanup = await module.render(main, router.current.params, router.current.query);
    } catch (err) {
      console.error(err);
      const { renderError } = await import("./components/states.js");
      renderError(main, err);
    }
  },

  start() {
    window.addEventListener("popstate", () => router.resolve());
    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link || link.target === "_blank" || link.hasAttribute("download") || event.metaKey || event.ctrlKey) return;
      const href = link.getAttribute("href");
      if (!href.startsWith("/") || href.startsWith("/api/") || href.startsWith("/static/")) return;
      event.preventDefault();
      router.navigate(href);
    });
    router.resolve();
  },
};
