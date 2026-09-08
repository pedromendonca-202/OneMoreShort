// Placeholder: replaced by the real screen implementation.
import { PageHeader } from "../components/header.js";
import { EmptyState } from "../components/states.js";

export async function render(container) {
  container.append(PageHeader("Hoje", "Seu painel de produção de vídeos curtos para o YouTube."), EmptyState({ title: "Em construção", text: "Esta tela ainda será implementada." }));
  return () => {};
}
