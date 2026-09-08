# Brief comum para a implementação de cada tela do painel

Leia inteiro antes de escrever código. Este arquivo complementa `docs/PROMPT-PAINEL-WEB.md` (regra 0: a
imagem de referência é o contrato) e `docs/superpowers/plans/2026-09-08-painel-web.md`.

## O que já existe (não reescrever)

- Backend FastAPI completo em `app/web/` (rotas, SSE, upload, chat). **Não altere o backend.** Se a tela
  precisar de um campo que a API não devolve, use o que existe e relate a lacuna no seu relatório final.
- Servidor de demonstração rodando em `http://127.0.0.1:8787` com o banco `database/demo.db`, populado
  por `scripts/seed_demo.py` com dados equivalentes às referências. Os arquivos estáticos são servidos
  sem cache: basta recarregar a página para ver o CSS/JS novo. Se o servidor não responder, inicie-o com
  `powershell -ExecutionPolicy Bypass -File scripts/demo.ps1` (roda em primeiro plano; use outro shell).
- Front: `app/web/static/` — `index.html` já carrega `css/tokens.css`, `css/base.css`,
  `css/components.css` e `css/screens/<tela>.css`; `js/app.js` registra as rotas e chama
  `render(container, params, query)` do módulo `js/screens/<tela>.js`. Sidebar e cabeçalho já estão
  prontos e idênticos à referência.

## Arquivos que você pode editar

Somente `app/web/static/js/screens/<tela>.js` e `app/web/static/css/screens/<tela>.css`. Componentes
específicos da tela ficam dentro do próprio módulo da tela (funções exportadas ou não). **Não edite**
`components.css`, `base.css`, `tokens.css`, `js/components/*`, `js/app.js`, nem nada em `app/web/*.py`.
Se um componente compartilhado precisar mudar, replique o estilo dentro do seu CSS (com o prefixo da
tela) e descreva a mudança desejada no relatório final. Prefixe todos os seletores do seu CSS com a
classe raiz da tela (`.scr-hoje`, `.scr-estudio`, `.scr-conversa`, `.scr-biblioteca`, `.scr-desempenho`,
`.scr-inteligencia`, `.scr-ajustes`) para não vazar estilo para outras telas.

## Ferramentas de UI disponíveis (ES modules)

```js
import { h, icon, svg, clear, on } from "../dom.js";
//  h("div", {class:"x", onClick: fn, dataset:{id}}, child, "texto")  -> Element (texto vira textContent)
//  icon("copy", "ic-sm")  -> <svg class="ic ic-sm"><use href="/static/icons.svg#copy"/></svg>
//  svg("circle", {cx:1})  -> elemento SVG (para gráficos escritos à mão)
import { api } from "../api.js";            // api.get(path) / api.post(path, body) / api.put / api.del / api.upload(path, formData, onProgress)
import { router } from "../router.js";      // router.navigate("/estudio/ID"), router.current.query
import { sse } from "../sse.js";            // const off = sse.on("state" | "job" | "clip" | "snapshot" | "settings", (data) => {...}); chame off() no cleanup
import { state } from "../state.js";        // state.job (job atual), state.subscribe(fn)
import { fmtViews, fmtInt, fmtPct, fmtDelta, fmtDateLong, weekday, fmtClock, fmtSeconds, fmtBytes, fmtElapsed, capitalize } from "../format.js";
import { PageHeader } from "../components/header.js";
import { Card, Pill, Button, LinkAction, IconCircle, NumCircle, CheckDot, Ring, MiniBars, Delta, DeltaPill, Thumb, LogoMark, Stepper, setContent } from "../components/ui.js";
import { EmptyState, Skeleton, SkeletonCard, Progress, HumanActionCard, NotFound } from "../components/states.js";
import { toast, confirmDialog, copyText } from "../components/feedback.js";
```

Leia `js/components/ui.js`, `states.js`, `feedback.js` e `css/components.css` para ver as classes
(`.card`, `.card-head`, `.pill-*`, `.btn-*`, `.icon-circle.*`, `.num-circle.*`, `.check-dot.*`, `.ring`,
`.stepper`, `.thumb`, `.delta`, `.field`, `.input`, `.select`, `.toggle`, `.slider`, `.tabs`, `.notice`,
`.empty`, `.skeleton`, `.progress`, `.human-action`). Ícones disponíveis: veja os `id` em
`app/web/static/icons.svg` (Lucide). Se faltar um ícone, desenhe-o inline com `svg()` no seu módulo.

## Contrato do módulo de tela

```js
export async function render(container, params, query) {
  container.append(PageHeader("Título", "Subtítulo exato da referência"));
  const root = h("div", { class: "scr-<tela>" });
  container.append(root);
  // 1. mostre Skeleton; 2. busque a API; 3. renderize; 4. assine SSE para atualizar
  return () => { /* cleanup: off() dos sse.on, clearInterval etc. */ };
}
```

## Regras inegociáveis

1. **Fidelidade**: abra `design/<n>-<tela>.png` (Read) antes de codar e compare a sua captura com ela ao
   final. Posição e tamanho de cada card, ordem, tamanhos/pesos de fonte, cores, raios, espaçamentos,
   ícones, textos de rótulo, badges e anotações. Corrija e repita até só restar conteúdo dinâmico.
   Viewport de referência 1491×1055. Grade: sidebar 258px; área principal começa em x=280 e termina em
   x=1470 (padding 20px 22px); gap entre cards 18px; padding de card 20px 22px.
2. **XSS**: nunca `innerHTML` com dado. Só `h()`/`textContent`.
3. **Estados**: carregando (Skeleton com a silhueta dos cards), vazio (EmptyState com ícone, frase e a
   ação que resolve), erro (toast.error + EmptyState), ação humana (HumanActionCard). Nada de spinner.
4. **Acessibilidade**: botões são `<button>`, links são `<a href>`; foco visível já vem do CSS base;
   `aria-label` em botões só com ícone; `aria-expanded` em acordeões; `role="dialog"` já vem no
   confirmDialog.
5. **Publicar e apagar** sempre passam por `confirmDialog(...)`.
6. Idioma da interface: português. Roteiro, prompts e títulos vindos da API aparecem como vêm.

## Captura e comparação

```
.venv\Scripts\python.exe scripts\capture.py /rota docs\captures\work\<tela>.png
.venv\Scripts\python.exe scripts\capture.py "/rota" saida.png --click ".seletor" --wait 800
```
O script imprime erros de console; a captura não é aceitável com erro de console. Depois use Read na
captura e na referência e liste as diferenças. Ao terminar, salve a captura final em
`docs/captures/<nn>-<tela>.png` (mesmo nome da referência em `design/`).

## Relatório final (obrigatório)

Liste: arquivos escritos; diferenças que ainda restam em relação à referência (seja honesto e
específico); lacunas da API que você contornou; sugestões de mudança em componentes compartilhados.
Não faça commit.
