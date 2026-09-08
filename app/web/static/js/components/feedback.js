// Toasts and confirmation dialogs.
import { h, icon } from "../dom.js";
import { Button } from "./ui.js";

const ICONS = { success: "circle-check", error: "circle-alert", info: "info" };

function push(kind, message, timeout = 4200) {
  const root = document.getElementById("toast-root");
  const el = h("div", { class: `toast ${kind}`, role: "status" }, icon(ICONS[kind] || "info"), h("span", {}, message));
  root.append(el);
  setTimeout(() => el.remove(), timeout);
  return el;
}

export const toast = {
  success: (m) => push("success", m),
  error: (m) => push("error", m, 6000),
  info: (m) => push("info", m),
};

export function confirmDialog({ title = "Confirmar?", body = "", confirmLabel = "Confirmar", cancelLabel = "Cancelar", danger = false, icon: iconName = null } = {}) {
  return new Promise((resolve) => {
    const root = document.getElementById("overlay-root");
    const previous = document.activeElement;
    let overlay;
    const close = (value) => { overlay.remove(); document.removeEventListener("keydown", onKey); previous?.focus?.(); resolve(value); };
    const onKey = (event) => { if (event.key === "Escape") close(false); };
    const confirmBtn = Button({ label: confirmLabel, icon: iconName, variant: danger ? "danger" : "primary", onClick: () => close(true) });
    overlay = h("div", { class: "overlay", onClick: (event) => { if (event.target === overlay) close(false); } },
      h("div", { class: `dialog ${danger ? "danger" : ""}`, role: "dialog", "aria-modal": "true", "aria-labelledby": "dlg-title" },
        h("h2", { id: "dlg-title" }, title), h("p", {}, body),
        h("div", { class: "dialog-actions" }, Button({ label: cancelLabel, variant: "secondary", onClick: () => close(false) }), confirmBtn)));
    root.append(overlay);
    document.addEventListener("keydown", onKey);
    confirmBtn.focus();
  });
}

export async function copyText(value, label = "Copiado") {
  try {
    await navigator.clipboard.writeText(value);
    toast.success(label);
    return true;
  } catch {
    const area = h("textarea", { style: { position: "fixed", opacity: "0" } });
    area.value = value;
    document.body.append(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    if (ok) toast.success(label); else toast.error("Não foi possível copiar.");
    return ok;
  }
}
