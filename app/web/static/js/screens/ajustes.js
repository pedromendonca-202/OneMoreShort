// Placeholder: replaced by the real screen implementation.
import { PageHeader } from "../components/header.js";
import { EmptyState } from "../components/states.js";

export async function render(container) {
  container.append(PageHeader("Ajustes", "Configure seu ambiente, chaves de API, publicação e automação."), EmptyState({ title: "Em construção", text: "Esta tela ainda será implementada." }));
  return () => {};
}
