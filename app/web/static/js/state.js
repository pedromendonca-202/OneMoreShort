// Small shared store for the sidebar indicators and cross-screen signals.
const subscribers = new Set();

export const state = {
  system: { status: "ready", label: "Pronto", spendUsd: 0, mode: "mock", connected: true },
  job: null,

  update(patch) {
    Object.assign(state, patch);
    subscribers.forEach((fn) => fn(state));
  },
  subscribe(fn) {
    subscribers.add(fn);
    return () => subscribers.delete(fn);
  },
};

export function systemFromJob(job, connected = true) {
  if (!connected) return { status: "error", label: "Sem conexão" };
  if (job && (job.status === "running" || job.status === "queued")) return { status: "busy", label: "Trabalhando" };
  if (job && job.status === "human_action") return { status: "warn", label: "Ação necessária" };
  if (job && job.status === "failed") return { status: "error", label: "Falha" };
  return { status: "ready", label: "Pronto" };
}
