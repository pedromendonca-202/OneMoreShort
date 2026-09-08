import { PageHeader } from "../components/header.js";
import { NotFound } from "../components/states.js";

export async function render(container) {
  container.append(PageHeader("Ops", "Essa página não existe."), NotFound());
  return () => {};
}
