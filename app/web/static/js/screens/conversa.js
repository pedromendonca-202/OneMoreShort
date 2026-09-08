// Placeholder: replaced by the real screen implementation.
import { PageHeader } from "../components/header.js";
import { EmptyState } from "../components/states.js";

export async function render(container) {
  container.append(PageHeader("Conversa", "Controle todo o sistema em linguagem natural. Fale com o seu assistente."), EmptyState({ title: "Em construção", text: "Esta tela ainda será implementada." }));
  return () => {};
}
