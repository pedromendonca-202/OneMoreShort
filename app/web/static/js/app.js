// Entry point: session, sidebar, router, live events.
import { loadSession, api } from "./api.js";
import { router } from "./router.js";
import { sse } from "./sse.js";
import { state, systemFromJob } from "./state.js";
import { renderSidebar } from "./components/sidebar.js";
import { toast } from "./components/feedback.js";

import * as hoje from "./screens/hoje.js";
import * as estudio from "./screens/estudio.js";
import * as conversa from "./screens/conversa.js";
import * as biblioteca from "./screens/biblioteca.js";
import * as desempenho from "./screens/desempenho.js";
import * as inteligencia from "./screens/inteligencia.js";
import * as ajustes from "./screens/ajustes.js";
import * as notfound from "./screens/notfound.js";

async function boot() {
  await loadSession();
  renderSidebar(document.getElementById("sidebar"));

  router.register("/", hoje);
  router.register("/estudio", estudio);
  router.register("/estudio/:id", estudio);
  router.register("/conversa", conversa);
  router.register("/biblioteca", biblioteca);
  router.register("/biblioteca/:id", biblioteca);
  router.register("/desempenho", desempenho);
  router.register("/desempenho/:id", desempenho);
  router.register("/inteligencia", inteligencia);
  router.register("/ajustes", ajustes);
  router.register("/ajustes/:tab", ajustes);
  router.setNotFound(notfound);
  router.start();

  sse.connect();
  sse.on("hello", (data) => state.update({ job: data?.job || null, system: { ...state.system, ...systemFromJob(data?.job) } }));
  sse.on("job", (job) => {
    state.update({ job, system: { ...state.system, ...systemFromJob(job) } });
    if (job.status === "failed") toast.error(`Falhou: ${job.error || job.name}`);
    if (job.status === "human_action") toast.error(job.error || "O sistema precisa de você.");
    if (job.status === "done" && ["prepare", "finish", "publish", "resume"].includes(job.name)) toast.success(JOB_DONE[job.name] || "Concluído.");
  });
  sse.on("connection", ({ ok }) => {
    if (!ok) state.update({ system: { ...state.system, status: "error", label: "Sem conexão" } });
    else if (state.system.status === "error") state.update({ system: { ...state.system, ...systemFromJob(state.job) } });
  });
  refreshSpend();
  setInterval(refreshSpend, 60_000);
}

const JOB_DONE = { prepare: "Roteiro e prompts prontos.", finish: "Vídeo final montado.", publish: "Publicado no YouTube.", resume: "Produção avançou." };

async function refreshSpend() {
  try {
    const costs = await api.get("/api/costs?days=1");
    state.update({ system: { ...state.system, spendUsd: costs.today_usd || 0 } });
  } catch { /* the sidebar keeps the last value */ }
}

boot().catch((err) => {
  console.error(err);
  document.getElementById("main").textContent = `Não foi possível iniciar o painel: ${err.message}`;
});
