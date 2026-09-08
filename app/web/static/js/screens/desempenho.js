// Placeholder: replaced by the real screen implementation.
import { PageHeader } from "../components/header.js";
import { EmptyState } from "../components/states.js";

export async function render(container) {
  container.append(PageHeader("Desempenho", "Acompanhe o desempenho dos seus vídeos e entenda o que gera mais engajamento."), EmptyState({ title: "Em construção", text: "Esta tela ainda será implementada." }));
  return () => {};
}
