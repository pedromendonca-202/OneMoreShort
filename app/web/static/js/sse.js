// Server-Sent Events: state / job / clip / snapshot / settings, with automatic reconnection.
const handlers = new Map();
let source = null;

function dispatch(type, payload) {
  for (const fn of handlers.get(type) || []) {
    try { fn(payload); } catch (err) { console.error(err); }
  }
  for (const fn of handlers.get("*") || []) {
    try { fn(type, payload); } catch (err) { console.error(err); }
  }
}

export const sse = {
  connect() {
    if (source) return;
    source = new EventSource("/api/events");
    for (const type of ["hello", "state", "job", "clip", "snapshot", "settings"]) {
      source.addEventListener(type, (event) => {
        let payload = {};
        try { payload = JSON.parse(event.data); } catch { payload = {}; }
        dispatch(type, payload.data !== undefined ? payload.data : payload);
      });
    }
    source.addEventListener("error", () => {
      dispatch("connection", { ok: false });
    });
    source.addEventListener("open", () => dispatch("connection", { ok: true }));
  },
  on(type, fn) {
    if (!handlers.has(type)) handlers.set(type, new Set());
    handlers.get(type).add(fn);
    return () => handlers.get(type)?.delete(fn);
  },
};
