# OneMoreShort — Construir o Painel Web

> **Como usar este arquivo:** cole o conteúdo inteiro no Claude Code, dentro da pasta
> `C:\Users\pepic\OneDrive\Área de Trabalho\OneMoreShort`. Ele é a especificação completa da tarefa.

---

## 0. A regra que domina todas as outras

**As telas construídas precisam ficar idênticas às referências visuais em `design/`.**

Não são inspiração. São o contrato. Cada card, cada ícone, cada badge, cada espaçamento, cada
gradiente, cada sombra e cada palavra de rótulo que aparece nas imagens precisa existir no produto
final, no mesmo lugar e com o mesmo peso visual.

Onde faltar tela ou estado que não foi desenhado, você **deduz a partir das sete referências** e
mantém a mesma linguagem: mesmos tokens, mesmos componentes, mesma densidade, mesmo tom de voz nos
textos. Nunca invente um estilo novo.

Se em algum ponto houver conflito entre este texto e a imagem, **a imagem vence.**

---

## 1. Contexto: o que já existe

Este repositório já contém uma fábrica autônoma de YouTube Shorts em Python, funcionando e testada.

- **126 testes passando** offline (`.\.venv\Scripts\python.exe -m pytest`, ~2min30, precisa de ffmpeg).
- Pipeline completo: tendências → tema → pesquisa → roteiro → storyboard → continuity bible →
  5 prompts → (operador gera os clipes no Google Flow) → validação → edição → narração → legendas →
  quality gate → metadados → upload YouTube → analytics → aprendizado.
- Orquestrador central: `app/pipeline/orchestrator.py` (classe `Orchestrator`).
- CLI atual: `app/cli.py` (`python -m app.cli <comando>`).
- Banco SQLite via SQLAlchemy: `app/core/models.py`, `database/oms.db`.
- Configuração: `app/core/config.py` + `config/default.yaml` (+ `config/local.yaml` opcional).
- Documentos: `ARCHITECTURE.md`, `PIPELINE.md`, `OPERATIONS.md`, `SETUP.md`, `API.md`,
  `TROUBLESHOOTING.md`, `DECISIONS.md`, `docs/SPEC.md`.

**Modo de operação escolhido pelo dono do projeto: custo zero.** Os cinco clipes de vídeo são
gerados manualmente por ele no Google Flow, usando os créditos da assinatura Google AI que já paga.
Nenhuma chamada paga à API do Veo é feita (`generation.mode: manual`). O cérebro do sistema roda na
camada gratuita do Gemini. As APIs do YouTube são gratuitas dentro da cota.

**Sua tarefa é construir a interface web deste sistema.** O motor não deve ser reescrito. O painel é
uma camada por cima do `Orchestrator` que já existe.

---

## 2. Referências obrigatórias

### 2.1 As sete telas desenhadas

| Arquivo | Tela | Rota |
|---|---|---|
| `design/01-hoje.png` | Hoje | `/` |
| `design/02-estudio.png` | Estúdio (passos 2 e 3 visíveis) | `/estudio/:id` |
| `design/03-conversa.png` | Conversa | `/conversa` |
| `design/04-biblioteca.png` | Biblioteca | `/biblioteca` |
| `design/05-desempenho.png` | Desempenho | `/desempenho/:id` |
| `design/06-inteligencia.png` | Inteligência | `/inteligencia` |
| `design/07-ajustes.png` | Ajustes | `/ajustes` |

Todas em **1491 × 1055**. Essa é a viewport de referência para conferência pixel a pixel.

**Abra e estude cada imagem antes de escrever qualquer linha de código.** Volte a elas durante a
implementação de cada tela. Você vai comparar seu resultado com elas ao final (seção 11).

### 2.2 O documento funcional

`docs/OneMoreShort-Painel-Web.pdf` — descreve o comportamento, o fluxo e a intenção de cada tela.
Use-o para entender **o que cada elemento faz**. Use as imagens para saber **como ele aparece**.
Onde o PDF e as imagens divergirem no visual, as imagens vencem.

---

## 3. Skills obrigatórias

Invoque na ordem, e siga cada uma de verdade:

1. **`superpowers:brainstorming`** — não pule. Antes de planejar, alinhe as decisões abertas da
   seção 12 com o dono do projeto.
2. **`superpowers:writing-plans`** — escreva o plano em
   `docs/superpowers/plans/2026-09-08-painel-web.md`, com tarefas do tamanho de um ciclo de teste.
3. **`frontend-design`** — obrigatória antes de escrever CSS ou componentes. Esta é uma tarefa de
   fidelidade visual, e essa skill governa como você a executa.
4. **`superpowers:test-driven-development`** — teste antes de implementação, em todo backend novo.
5. **`superpowers:subagent-driven-development`** — para executar o plano tarefa a tarefa.
6. **`superpowers:verification-before-completion`** — nada é declarado pronto sem evidência.
7. **`security-review`** — revisão de segurança do que você construiu (seção 10).
8. **`code-review`** — revisão de correção e qualidade antes de fechar.
9. **`chrome-devtools-mcp:chrome-devtools`** ou **`playwright`** — para capturar as telas
   construídas e compará-las com as referências.

---

## 4. Subagentes

Use, no mínimo:

- **`feature-dev:code-explorer`** — mapear o `Orchestrator`, os modelos e o que já existe, antes de
  desenhar a API. Não duplique lógica que já está implementada.
- **`feature-dev:code-architect`** — desenhar a camada web (rotas, contratos, estado do front) em
  cima do que existe.
- Um subagente **por tela** na fase de implementação, cada um com a imagem de referência
  correspondente e o design system da seção 6. Rode em paralelo quando as telas forem independentes,
  respeitando a ordem da seção 13.
- **`pr-review-toolkit:silent-failure-hunter`** — caçar erros engolidos, principalmente no upload de
  arquivos, nas chamadas ao YouTube e nas ferramentas do chat.
- **`pr-review-toolkit:code-reviewer`** e **`feature-dev:code-reviewer`** — revisão final.
- **`code-simplifier:code-simplifier`** — passada de simplificação ao final, sem alterar o visual.

---

## 5. Stack

**Backend:** FastAPI no mesmo `.venv` que já existe. Adicione `fastapi` e `uvicorn` ao
`requirements.txt` e ao `pyproject.toml`. Nada além disso sem justificar.

**Frontend:** HTML + CSS + JavaScript ES modules, **sem etapa de build, sem npm, sem framework**.
Motivos: o projeto inteiro é Python sem Node; o painel roda offline; e menos peças significa menos
manutenção. Se você julgar que isso inviabiliza a fidelidade visual, levante o ponto no
brainstorming antes de decidir sozinho.

**Ativos, todos locais** (o painel precisa funcionar sem internet):

- **Fonte:** Inter (Regular 400, Medium 500, SemiBold 600, Bold 700, ExtraBold 800), em
  `app/web/static/fonts/`. É a que mais se aproxima das referências. `font-feature-settings` com
  `"cv11"` para o `1` de bico reto. Fallback: `system-ui, "Segoe UI", sans-serif`.
- **Ícones:** Lucide, como sprite SVG único em `app/web/static/icons.svg`, usado via `<use>`. Os
  ícones das referências são Lucide ou muito próximos. Mapeie um a um observando as imagens.
- **Gráficos:** SVG escrito à mão, sem biblioteca. A curva de retenção, as sparklines, as barras de
  confiança, o gráfico comparativo e o scatter do mapa de formatos são todos viáveis em SVG puro e
  ficam mais fiéis do que qualquer lib genérica.
- **Ilustrações 3D** (logo grande do sidebar, arte do banner da tela Hoje): recorte-as das
  referências como PNG com transparência e guarde em `app/web/static/img/`. Documente a origem.

**Estrutura sugerida:**

```
app/web/
├── server.py            FastAPI: rotas de API, SSE, upload, estáticos
├── deps.py              injeção do Orchestrator e das Settings
├── schemas.py           modelos Pydantic de request/response
├── chat.py              assistente Gemini com ferramentas
├── security.py          CSRF, validação de caminho, limites
└── static/
    ├── index.html
    ├── css/  tokens.css  base.css  components.css  screens/*.css
    ├── js/   app.js  router.js  api.js  sse.js  components/*.js  screens/*.js
    ├── fonts/  icons.svg  img/
```

---

## 6. Design system extraído das referências

Os valores abaixo foram amostrados diretamente das imagens. Use-os como tokens CSS. Se ao comparar
uma tela você notar diferença, **ajuste o token para bater com a imagem**, não o contrário.

### 6.1 Cores

```css
:root{
  /* superfícies */
  --bg:            #0B0E11;   /* fundo da área principal */
  --bg-sidebar:    #0E1115;   /* barra lateral */
  --surface:       #12171B;   /* cards e painéis */
  --surface-2:     #0F1419;   /* áreas internas, inputs, blocos de prompt */
  --surface-3:     #161B23;   /* botão secundário, chips */
  --border:        #1E242C;   /* borda padrão de card */
  --border-soft:   #171C23;   /* divisórias internas */

  /* vermelho da marca — só para ação principal e para o que exige o operador */
  --red:           #FF2233;
  --red-bright:    #FD3541;   /* topo do gradiente dos botões */
  --red-deep:      #C1101F;   /* base do gradiente */
  --red-dim:       #611821;   /* fundo de pill/nav ativa */
  --red-glow:      rgba(255,34,51,.32);

  /* estados */
  --green:         #3DF193;   /* pontos, checks, anéis */
  --green-solid:   #35AB67;   /* fundo de pill "Publicado" */
  --green-dim:     #1D5437;
  --amber:         #F5AB14;
  --amber-dim:     #412B0E;
  --blue:          #3B82F6;
  --purple:        #B272F3;
  --grey-pill:     #525764;

  /* texto */
  --text:          #F7F6F7;
  --text-2:        #99A1AC;
  --text-3:        #6B7480;

  /* forma */
  --r-sm: 8px; --r-md: 12px; --r-lg: 16px; --r-xl: 20px; --r-pill: 999px;
  --shadow-card: 0 1px 0 rgba(255,255,255,.03) inset, 0 8px 24px rgba(0,0,0,.35);
  --shadow-red:  0 6px 20px rgba(255,34,51,.28);
}
```

Regras de uso:

- **Vermelho é escasso.** Ação principal, item de navegação ativo, o que exige o operador, e o
  traço da curva de retenção. Nada mais.
- **Verde** é resultado positivo e saúde. **Âmbar** é atenção que não bloqueia. **Roxo** e **azul**
  só aparecem como cor de categoria em ícones e tags.
- Todo card tem borda de 1px em `--border` e cantos `--r-lg`.

### 6.2 Tipografia

| Uso | Tamanho | Peso | Tracking |
|---|---|---|---|
| Título de página ("Hoje", "Estúdio") | 40px | 800 | -0.03em |
| Título do banner ("Gerar os 5 clipes…") | 30px | 800 | -0.02em |
| Título de card | 20px | 700 | -0.01em |
| Número grande (KPI, stat) | 34px | 800 | -0.02em |
| Corpo | 14px | 400 | 0 |
| Corpo forte / rótulo de linha | 14px | 600 | 0 |
| Secundário / descrição | 13px | 400 | 0 |
| Etiqueta caixa alta ("PRODUÇÃO DE HOJE") | 11px | 700 | 0.14em |
| Mono (prompts, IDs) | 12px | 400 | 0 |

Fonte mono: `Consolas, "Cascadia Mono", monospace`.

### 6.3 Layout

- Sidebar: **258px** fixa, altura total, `--bg-sidebar`, sem borda direita visível (o contraste de
  fundo já separa).
- Área principal: `padding: 28px 32px`, largura fluida.
- Grade de conteúdo: 12 colunas, `gap: 20px`. As referências usam repetidamente 2/3 + 1/3 e 4 colunas
  iguais.
- Espaçamento vertical entre cards: **20px**.
- Padding interno de card: **20px 22px**.

### 6.4 Barra lateral, em detalhe

De cima para baixo, exatamente como nas imagens:

1. **Logo 3D** OneMoreShort (play vermelho em relevo + wordmark), centralizado, ~200px de largura.
2. **Tagline** "IDEIAS HOJE, / VÍDEOS SEMPRE." — 11px, 600, tracking 0.16em, `--text-3`, centralizado.
3. **Sete itens de navegação**: Hoje, Estúdio, Conversa, Biblioteca, Desempenho, Inteligência,
   Ajustes. Ícone 22px + rótulo 16px/600. Altura 52px, raio `--r-md`, padding lateral 18px.
   - Repouso: transparente, ícone e texto em `--text-2`.
   - Hover: fundo `rgba(255,255,255,.04)`.
   - **Ativo**: gradiente `linear-gradient(100deg, #7E1A24, #3C0F15)`, borda 1px `#B8202C`,
     texto branco, ícone branco, e um brilho externo suave em `--red-glow`.
4. **Empurrador flexível.**
5. **Cartão "Sistema / Pronto"**: ponto verde pulsante 10px, rótulo 12px `--text-2`, valor 16px/700
   branco, chevron à direita. Fundo `--surface`, borda `--border`, raio `--r-md`.
6. **Cartão "Gasto hoje / R$ 0,00"**: mesmo formato, ícone de carteira.
7. **Rodapé**: "Mais ideias. / Mais conteúdo. / Um mundo mais curioso." em 12px `--text-3`, com um
   traço vermelho desenhado à mão abaixo (SVG).

### 6.5 Cabeçalho de página

Presente em todas as telas: título 40px/800 à esquerda com subtítulo 14px `--text-2` embaixo; à
direita, ícone de calendário + "8 de setembro de 2026 / Terça-feira" em duas linhas, e uma pill
`--surface-3` com ponto verde e o texto "localhost:8787".

### 6.6 Inventário de componentes

Construa cada um uma única vez, em `js/components/`, e reutilize. A lista saiu das sete imagens:

`SidebarNav` · `PageHeader` · `Card` (com slot de ícone, título, subtítulo e ação no canto) ·
`HeroBanner` (Hoje) · `Stepper` (horizontal, com estados concluído/atual/pendente e linha
conectora) · `StatCard` (ícone em círculo colorido, número, delta, sparkline) · `KpiCard`
(Desempenho, com delta e linha de comparação) · `Timeline` (checks verdes + conector vertical) ·
`VideoListItem` (miniatura + título + data + views + anel de retenção) · `RetentionRing` ·
`Sparkline` · `PromptAccordion` (expandido com blocos SCENE CONTEXT / CAMERA / NEGATIVE em mono, e
colapsado) · `ClipCard` (miniatura, duração, tamanho, badge de status, botão Substituir, kebab) ·
`Dropzone` · `ChatBubble` (usuário vermelho à direita, assistente card escuro à esquerda com cards
ricos dentro) · `QuickCommandCard` · `ActivityTimeline` (pontos coloridos + hora) · `VideoGridCard`
(Biblioteca) · `DetailPanel` (painel lateral da Biblioteca, com botão fechar) · `RetentionChart`
(SVG, com marcadores e balões de anotação) · `ScriptTimeline` (Desempenho, com a cena atual
destacada em vermelho) · `OutcomeList` (O que funcionou / falhou / recomendação, com ícones
circulares verdes, vermelhos e âmbar) · `ComparisonChart` · `InsightRow` (número, texto, tags,
barra de confiança, contagem de vídeos) · `PerformanceTable` (barras dentro da tabela) ·
`ScatterPlot` · `TestCard` (Inteligência) · `Tabs` (Ajustes) · `TextField` `SelectField`
`Toggle` `Slider` `PasswordField` (com olho de revelar) · `StatusList` (Saúde do sistema) ·
`Pill` (variantes: vermelho, verde, âmbar, roxo, cinza) · `Button` (primário com gradiente vermelho
e sombra, secundário `--surface-3`, fantasma, desabilitado) · `Toast` · `ConfirmDialog` ·
`EmptyState` · `Skeleton`.

---

## 7. As telas

Para cada uma: abra a imagem, reproduza a estrutura, os textos e os estados. Abaixo estão os pontos
de atenção e a ligação com os dados reais do backend.

### 7.1 Hoje — `design/01-hoje.png`

- **Banner** com gradiente vermelho escuro à esquerda para preto à direita, arte 3D do logo à
  direita, rótulo "PRODUÇÃO DE HOJE" + o ID da produção, "Próxima ação" em `--text-2`, o título da
  ação em 30px/800, a descrição, e dois botões: "Abrir o Estúdio" (primário) e "Copiar prompt 1"
  (secundário com ícone de copiar). A anotação manuscrita "TRANSFORME IDEIAS EM VÍDEOS REAIS" fica
  no canto superior direito.
- **Stepper de 6 passos** na base do banner: Tendências, Roteiro, Prompts, Clipes, Edição,
  Publicação. Concluídos = círculo vermelho preenchido com check branco. Atual = círculo com borda
  vermelha e número. Pendente = círculo cinza `#3D4553`. Linhas conectoras vermelhas até o passo
  atual, cinza depois.
- **Tema escolhido**: título do tema, pills de categoria e score, texto justificando a escolha,
  miniatura vertical à direita, botão "Ver outros temas".
- **Estado da produção**: timeline com horários e checks verdes; o item pendente fica com círculo
  vazio e contador "0/5". Badge âmbar "Aguardando clipes" no cabeçalho do card.
- **Últimos publicados**: três linhas com miniatura, título, data, views e anel de retenção.
- **Resumo do canal**: três números com delta verde e um gráfico de linha vermelho com a anotação
  manuscrita "EVOLUÇÃO CONSTANTE".

O bloco do banner é sempre **a única coisa que pede ação**. Ele muda conforme o estado: aguardando
clipes, processando (com barra de progresso e etapa atual), pronto para revisão, publicado, falha,
ou "tudo em dia" com o próximo horário agendado.

### 7.2 Estúdio — `design/02-estudio.png`

- **Stepper de 5 passos** no topo, em card próprio, com o ID da produção à direita em vermelho.
- **Prompts para o Flow**: a cena 1 aberta, com borda vermelha, miniatura vertical à esquerda,
  número em círculo vermelho, título "Cena 1 · 0s → 8s", legenda "O impacto visual", botão "Copiar",
  chevron, e o corpo em mono com os rótulos `SCENE CONTEXT:`, `CAMERA:` e `NEGATIVE:` em vermelho.
  As cenas 2 a 5 colapsadas, com miniatura, número, faixa de tempo e botão copiar.
- Rodapé do card com ícone de informação e a regra de continuidade.
- **Resumo da produção**: miniatura, tema, pill de categoria, e quatro blocos com ícone: Duração
  total, Formato, Status atual (âmbar), Cenas.
- **Ações rápidas**: Copiar todos, Baixar roteiro, Ir para revisão (desabilitado com explicação).
- **Clipes gerados**: dropzone tracejada, e a fileira de cinco cards de clipe com miniatura, nome,
  duração, tamanho, badge de status (verde ok, âmbar atenção, cinza aguardando) e botão Substituir.
  O quinto é um card vazio com botão "Enviar arquivo".
- Faixa âmbar de aviso na base e o botão "Continuar para revisão" à direita.

**Passos 1, 4 e 5 não foram desenhados. Construa-os na mesma linguagem:**
- **1 · Roteiro:** o roteiro por batidas, com marcação de tempo, tipo de gancho e tipo de final,
  no mesmo formato de card e mesma tipografia mono onde couber. Ação: "Refazer roteiro".
- **4 · Revisão:** player vertical 9:16 à esquerda; à direita, a lista do quality gate item a item
  com os mesmos ícones circulares verdes e vermelhos da tela Desempenho.
- **5 · Publicar:** título, descrição e hashtags editáveis em campos no estilo da tela Ajustes,
  escolha de visibilidade e horário, e o botão primário "Publicar no YouTube" exigindo confirmação.

### 7.3 Conversa — `design/03-conversa.png`

- **Cabeçalho do assistente** com avatar do logo, nome, pill verde "online" e a anotação manuscrita.
- **Bolhas**: usuário em vermelho sólido à direita com avatar circular; assistente em card escuro à
  esquerda, podendo conter cards ricos com miniatura, título, pills e botões de ação
  ("Ver os prompts", "Ver roteiro", "Gerar prompts", "Abrir relatório"). Horário à esquerda de cada
  bolha.
- **Campo de entrada** arredondado com clipe de anexo, placeholder, dica "Ctrl + Enter para enviar"
  e botão circular vermelho de envio.
- **Coluna direita**: "Comandos rápidos" (5 cards com ícone, título e descrição), "Ações recentes"
  (timeline com pontos coloridos e hora) e "O que o assistente faz" (4 cards).

O assistente executa de verdade, com ferramentas (seção 9). Publicar e apagar sempre abrem
`ConfirmDialog`, mesmo pedidos por texto.

### 7.4 Biblioteca — `design/04-biblioteca.png`

- Barra de filtros: busca com ícone, três selects e o botão primário "+ Novo vídeo".
- Quatro **StatCards** com ícone em círculo colorido (verde, âmbar, azul, roxo), número, delta e
  mini barras.
- **Grade de cards de vídeo**: miniatura vertical com duração no canto, kebab, título, pill de
  status (Publicado verde, Em produção âmbar, Falha vermelho, Rascunho cinza), data, views, anel de
  retenção e tag de categoria.
- **Painel de detalhe** à direita quando um card é selecionado: miniatura grande, título, ID,
  descrição, lista de metadados com ícones, botão primário "Abrir desempenho" e secundário
  "Duplicar fluxo", com X para fechar.

### 7.5 Desempenho — `design/05-desempenho.png`

- Faixa superior com miniatura, data, título grande, ID e dois botões: "Voltar à biblioteca" e
  "Exportar relatório".
- Quatro **KpiCards** com ícone circular, rótulo, número grande, delta em pill verde e a linha
  "vs. média do canal (…)".
- **Curva de retenção** em SVG: eixo Y 0–100%, eixo X 0–40s, linha vermelha com área sob a curva,
  linhas verticais tracejadas nos pontos de queda e balões de anotação com o valor, o instante e a
  explicação. O balão maior cita a cena e a frase do roteiro.
- **Roteiro do vídeo** à direita: lista de cenas com faixa de tempo, título e trecho da narração; a
  cena correspondente à queda destacada em vermelho.
- Três cards: **O que funcionou** (checks verdes), **O que falhou** (X vermelhos), **Recomendação
  para o próximo** (setas âmbar), cada item com título e explicação.
- **Comparativo de retenção**: duas curvas sobrepostas com legenda e o rótulo de ganho ao final, mais
  um card com troféu e o resultado.

### 7.6 Inteligência — `design/06-inteligencia.png`

- Quatro cards de destaque no topo, cada um com ícone circular colorido, número grande, comparação e
  a base amostral em pill.
- **Padrões detectados**: linhas numeradas em círculo vermelho, título com o ganho em destaque, tags,
  barra de confiança com percentual e a contagem de vídeos.
- **Temas por performance**: tabela com ícone por tema, barra de retenção e inscritos por mil views.
- **Estruturas narrativas**: três cards com ícone, nome do formato, descrição e pill de resultado.
- **Mapa de formatos**: scatter em SVG, eixo X duração, eixo Y retenção, tamanho do ponto = views,
  cor = tema, com a "Zona ideal" marcada em retângulo tracejado e legenda ao lado.
- **Próximos testes recomendados**: três cards com número do teste, hipótese, impacto esperado,
  confiança e botão "Adicionar ao Estúdio".
- Rodapé com nota de peso estatístico e data de atualização.

### 7.7 Ajustes — `design/07-ajustes.png`

- **Abas**: Geral, IA, YouTube, Marca, Automação, Arquivos. A aba ativa tem fundo vermelho escuro e
  borda vermelha.
- Cards: **Google AI Studio** (chave mascarada com olho, select de modelo, resultado do teste de
  conexão e botão "Testar conexão"), **YouTube OAuth** (avatar da conta, escopos com checks verdes,
  botões Desconectar e Reconectar), **Saúde do sistema** (lista com pills de estado), **Publicação
  padrão**, **Marca do canal**, **Regras de produção** (sliders com valor em caixa e três toggles),
  **Arquivos locais** (caminhos com botões Selecionar e Abrir).
- Rodapé fixo com "Restaurar padrões" à esquerda e "Salvar alterações" primário à direita.

**Importante:** a chave da API nunca volta do servidor em texto claro. O campo mostra apenas o
prefixo e asteriscos, como na imagem. O olho revela somente o que o operador acabou de digitar.

---

## 8. Telas e estados que faltam

Não foram desenhados, mas são necessários. Construa-os fiéis à linguagem das sete referências:

- Estúdio passos 1, 4 e 5 (detalhado em 7.2).
- **Vazio**: nenhuma produção hoje; biblioteca sem vídeos; vídeo sem analytics ainda; inteligência
  sem amostra suficiente. Use `EmptyState` com ícone grande, frase curta e a ação que resolve.
- **Carregando**: `Skeleton` com a mesma silhueta dos cards, nunca spinner solto.
- **Processando**: barra de progresso com a etapa atual e tempo decorrido, alimentada por SSE.
- **Erro e ação humana**: quando o backend levanta `HumanActionRequired`, mostre o relatório
  completo (PROBLEMA, CAUSA RAIZ, O QUE FOI AUTOMATIZADO, O QUE FALTA, AÇÃO HUMANA NECESSÁRIA,
  PRÓXIMO PASSO AUTOMÁTICO) em um card com a borda vermelha e o botão que resolve.
- **Primeira execução**: se faltam a chave do Gemini ou o OAuth do YouTube, uma tela de configuração
  guiada, no estilo de Ajustes, com os passos numerados.
- **Confirmação** para publicar, apagar e restaurar padrões.
- **Toasts** de sucesso e falha, no canto inferior direito.
- **404** de rota, no estilo `EmptyState`.

---

## 9. API e integração com o motor

Exponha o `Orchestrator` existente. Não reimplemente regra de negócio no servidor web.

| Método | Rota | Faz |
|---|---|---|
| GET | `/api/today` | Produção do dia, estado, próxima ação, resumo do canal |
| POST | `/api/productions` | `new_production(force)` |
| GET | `/api/productions` | `list_productions(limit)` para a Biblioteca |
| GET | `/api/productions/{id}` | `status(id)` + artefatos |
| POST | `/api/productions/{id}/prepare` | `prepare(id)` |
| GET | `/api/productions/{id}/prompts` | Os cinco prompts, texto integral |
| POST | `/api/productions/{id}/clips` | Upload multipart dos clipes (ver segurança) |
| POST | `/api/productions/{id}/collect` | `collect(id)` |
| POST | `/api/productions/{id}/finish` | `finish(id)` |
| POST | `/api/productions/{id}/publish` | Publicação explícita, com confirmação |
| GET | `/api/productions/{id}/report` | `report(id)` |
| GET | `/api/analytics/{id}` | Snapshots, curva, quedas mapeadas ao roteiro |
| POST | `/api/analytics/collect` | `collect_analytics()` |
| POST | `/api/learn` | `learn()` |
| GET | `/api/intelligence` | Insights, padrões, temas, estruturas, testes |
| GET | `/api/metrics` · `/api/costs` | `metrics()` · `costs()` |
| GET/PUT | `/api/settings` | Configuração; segredos só de escrita |
| POST | `/api/settings/test-connection` | Testa a chave do Gemini |
| GET | `/api/health` | Equivalente ao `doctor`, alimenta "Saúde do sistema" |
| POST | `/api/chat` | Mensagem para o assistente |
| GET | `/api/events` | SSE: mudança de estado, progresso, novo snapshot |

**Chat com ferramentas.** O assistente é Gemini com function calling. Ferramentas permitidas, e
nenhuma além destas: `iniciar_producao`, `trocar_tema`, `refazer_roteiro`, `ver_prompts`,
`montar_video`, `consultar_desempenho`, `consultar_inteligencia`, `consultar_custos`,
`preparar_publicacao`. Publicar e apagar **não são ferramentas** — o assistente apenas abre o
diálogo de confirmação na interface.

**Miniaturas.** As referências mostram thumbnails em toda parte. Gere-as extraindo um quadro do
vídeo final com ffmpeg (já existe `extract_frame_at`), guarde em `storage/thumbs/<id>.jpg` e sirva
por uma rota dedicada. Enquanto não houver vídeo, use o primeiro quadro do clipe da cena 1.

---

## 10. Segurança

Requisitos, não sugestões. A skill `security-review` roda ao final e precisa passar limpa.

1. **Só localhost.** Uvicorn ligado em `127.0.0.1`. Nunca `0.0.0.0`. Documente isso.
2. **CSRF.** Todo endpoint que muda estado exige um token gerado por sessão e enviado em cabeçalho
   próprio. Rejeite requisições sem ele. Cookies, se houver, com `SameSite=Strict`.
3. **Upload de clipes.** Este é o ponto mais sensível:
   - Ignore o nome de arquivo enviado. Gere o nome no servidor a partir do índice da cena.
   - Escreva **somente** dentro de `storage/manual_input/<id>/`, com o caminho resolvido e
     verificado como descendente dessa pasta. Rejeite `..`, caminhos absolutos e symlinks.
   - Limite de tamanho por arquivo e no total. Rejeite acima do limite antes de ler o corpo inteiro.
   - Valide o conteúdo com ffprobe antes de aceitar. Extensão e content-type não são prova.
   - Só cinco arquivos por produção.
4. **Segredos.** A chave do Gemini e o token do YouTube nunca aparecem em resposta de API, em log,
   em mensagem de erro ou no HTML. O `PUT /api/settings` escreve a chave em `.env`, nunca em YAML
   versionado. Máscara na leitura, como na imagem.
5. **XSS.** Todo dado que chega ao DOM é tratado como não confiável: título de vídeo, resposta do
   modelo, mensagem do chat, título vindo de RSS, nome de arquivo. Use `textContent`. Nada de
   `innerHTML` com dado dinâmico. Se precisar de HTML rico, sanitize com allowlist explícita.
6. **Injeção de prompt.** Títulos e resumos vindos de RSS, Reddit e YouTube entram nos prompts do
   LLM. Trate-os como dados, delimitados e rotulados como não confiáveis, nunca como instruções.
   O mesmo vale para o texto que o operador digita no chat quando ele aciona ferramentas.
7. **SSRF.** As fontes de tendência têm URLs fixas no código. Não aceite URL vinda do cliente para
   busca. Não adicione um endpoint de proxy.
8. **Ferramentas do chat.** Lista fechada, sem execução de shell, sem leitura arbitrária de arquivo,
   sem SQL livre. Cada ferramenta valida seus argumentos com Pydantic.
9. **Cabeçalhos.** `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`,
   `Referrer-Policy: no-referrer`, e uma CSP restritiva. Sem CORS: mesma origem apenas.
10. **Estados que nunca publicam.** O backend já recusa publicar de `BLOCKED`, `FAILED`,
    `NEEDS_REVIEW` e `NEEDS_HUMAN_ACTION`. A interface não pode oferecer o botão nesses estados, e
    o servidor precisa recusar mesmo se a requisição chegar.
11. **Limite de taxa** simples nos endpoints que gastam cota ou dinheiro: chat, coleta de analytics,
    teste de conexão.
12. **Dependências** com versão fixada em `requirements.txt`.

---

## 11. Fidelidade visual: como comprovar

Esta é a condição de aceite principal. Não declare uma tela pronta sem executar isto.

1. Suba o servidor.
2. Com Chrome DevTools MCP ou Playwright, defina a viewport em **1491 × 1055** e capture cada tela
   com dados de exemplo equivalentes aos das referências.
3. Salve em `docs/captures/<tela>.png`.
4. **Compare lado a lado com `design/<tela>.png` e liste as diferenças.** Corrija e repita até que
   as diferenças restantes sejam apenas conteúdo dinâmico legítimo.
5. Confira explicitamente: posição e tamanho de cada card, ordem dos elementos, tamanhos e pesos de
   fonte, todas as cores, raios de canto, espaçamentos, ícones escolhidos, textos de rótulo,
   estados de badge e a presença das anotações manuscritas.
6. Verifique também os estados de hover, foco e desabilitado, e a navegação por teclado.

Anexe as capturas ao relatório final.

---

## 12. Decisões a alinhar no brainstorming

Leve estas perguntas ao dono do projeto antes de escrever o plano:

1. As anotações manuscritas ("TRANSFORME IDEIAS EM VÍDEOS REAIS", "EVOLUÇÃO CONSTANTE", "DADOS
   TRANSFORMAM IDEIAS EM VÍDEOS MELHORES") são recorte das referências ou devem ser recriadas em SVG?
2. Os dados das referências são fictícios. Confirmar que a interface deve mostrar os dados reais do
   banco e que estados vazios são esperados no começo.
3. O idioma da interface é português, mas o conteúdo dos vídeos é inglês americano. Confirmar que os
   prompts e o roteiro aparecem em inglês dentro de uma interface em português, como nas imagens.
4. A Biblioteca mostra "Novo vídeo" e "Duplicar fluxo". Confirmar se duplicar fluxo deve reaproveitar
   tema e roteiro ou apenas o formato.
5. Confirmar a stack sem framework antes de começar (seção 5).

---

## 13. Ordem de execução

Cada fase termina com testes verdes, capturas comparadas e um commit.

| Fase | Entrega |
|---|---|
| 0 | Explorar o código com `code-explorer`, brainstorming, plano escrito |
| 1 | Servidor FastAPI, estáticos, tokens CSS, fonte, ícones, Sidebar, PageHeader, roteador |
| 2 | Tela **Hoje** completa, com SSE e todos os estados do banner |
| 3 | Tela **Estúdio**: os cinco passos, upload, validação, revisão, publicação |
| 4 | Telas **Biblioteca** e **Desempenho**, com os gráficos SVG |
| 5 | Tela **Inteligência**, com scatter e tabelas |
| 6 | Tela **Ajustes**, escrita segura de configuração, saúde do sistema |
| 7 | Tela **Conversa**, assistente com ferramentas |
| 8 | Estados vazios, carregando, erro, ação humana, confirmações, toasts, 404 |
| 9 | Revisão de segurança, revisão de código, caça a falhas silenciosas, simplificação |
| 10 | Capturas finais das sete telas comparadas com as referências, documentação, atalho de inicialização |

---

## 14. Definição de pronto

- [ ] As sete telas conferidas contra as referências, com as capturas anexadas.
- [ ] Telas e estados não desenhados construídos na mesma linguagem visual.
- [ ] Os 126 testes existentes continuam passando, mais os novos do backend web.
- [ ] `security-review` sem achados abertos; os doze itens da seção 10 verificados um a um.
- [ ] `code-review` e `silent-failure-hunter` sem achados abertos.
- [ ] O painel roda offline, sem internet, sem npm, com um atalho na área de trabalho.
- [ ] Nenhum segredo em resposta de API, log ou HTML.
- [ ] `README.md`, `OPERATIONS.md` e `API.md` atualizados com o painel.
- [ ] Commits pequenos, mensagens descritivas, árvore limpa ao final.

---

## 15. Como se comportar durante a execução

- Não reescreva o motor. Se precisar mudar algo em `app/`, faça o menor ajuste possível e explique.
- Não introduza dependência nova sem justificar.
- Se uma referência for ambígua, olhe as outras seis antes de perguntar. A resposta quase sempre
  está no padrão que se repete.
- Se algo estiver bloqueado, entregue todo o resto e diga com clareza o que ficou de fora e por quê.
- Reporte com honestidade: se uma tela ainda não está idêntica, diga onde diverge.
