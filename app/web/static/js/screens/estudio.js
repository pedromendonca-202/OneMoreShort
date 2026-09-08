// Placeholder: replaced by the real screen implementation.
import { PageHeader } from "../components/header.js";
import { EmptyState } from "../components/states.js";

export async function render(container) {
  container.append(PageHeader("Estúdio", "Do roteiro à publicação. Produza seu vídeo completo, passo a passo."), EmptyState({ title: "Em construção", text: "Esta tela ainda será implementada." }));
  return () => {};
}
