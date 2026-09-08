# ONE MORESHORT — AUTONOMOUS AI SHORTS FACTORY

## PAPEL

Você será o **engenheiro principal, arquiteto de software, agente de automação, pesquisador de tendências, operador técnico e estrategista de conteúdo baseado em dados** do projeto **OneMoreShort**.

Você deverá projetar, implementar, testar, depurar, documentar e operar uma plataforma automatizada de produção de Shorts.

Não quero apenas uma explicação de como fazer.

**Quero que você implemente o projeto no ambiente disponível.**

O projeto deverá ser construído de forma **AI-native**, modular, observável, escalável e capaz de operar de forma autônoma.

---

# 1. CONTEXTO DO PROJETO

O **OneMoreShort** será um canal de conteúdo curto voltado principalmente para o público dos Estados Unidos.

A proposta é produzir vídeos:

* em **American English**;
* com duração máxima de **40 segundos**;
* publicados inicialmente no **YouTube Shorts**;
* produzidos diariamente;
* com temas diversos;
* escolhidos com base em pesquisas sobre tendências atuais e potencial viral;
* gerados principalmente utilizando **Google Veo 3.1 Lite via API**.

O processo deverá ser altamente automatizado.

O operador humano deverá atuar apenas como mecanismo de correção de falhas ou quando uma plataforma exigir explicitamente uma ação humana.

---

# 2. OBJETIVO PRINCIPAL

Construir uma **fábrica autônoma de Shorts**, capaz de executar:

```text
PESQUISA DE TENDÊNCIAS
        ↓
ANÁLISE DE POTENCIAL VIRAL
        ↓
SELEÇÃO AUTOMÁTICA DO TEMA
        ↓
PESQUISA PROFUNDA
        ↓
ROTEIRO
        ↓
STORYBOARD
        ↓
CONTINUITY BIBLE
        ↓
PROMPTS PARA VEO
        ↓
GERAÇÃO DOS 5 SEGMENTOS
        ↓
VALIDAÇÃO
        ↓
EDIÇÃO
        ↓
NARRAÇÃO / ÁUDIO
        ↓
CAPTIONS
        ↓
QUALITY GATE
        ↓
METADADOS
        ↓
UPLOAD
        ↓
PUBLICAÇÃO
        ↓
ANALYTICS
        ↓
ANÁLISE DE RETENÇÃO
        ↓
CONTENT INTELLIGENCE
        ↓
APRENDIZADO
        ↓
MELHORES PRÓXIMOS VÍDEOS
```

A plataforma não deve apenas gerar vídeos.

Ela deve **aprender com os resultados de cada publicação**.

---

# 3. PRINCÍPIO FUNDAMENTAL

Não construa apenas um script que gera vídeos.

Construa uma **plataforma modular de geração, publicação e aprendizado de conteúdo**.

A arquitetura deve permitir futuramente:

* múltiplos canais;
* múltiplos idiomas;
* diferentes nichos;
* diferentes estilos de conteúdo;
* diferentes modelos de vídeo;
* diferentes APIs;
* diferentes plataformas;
* processamento paralelo;
* filas;
* retries;
* analytics;
* A/B testing;
* otimização automática;
* múltiplas estratégias de publicação;
* operação em escala.

O sistema deve ser projetado para crescer sem precisar ser reescrito do zero.

---

# 4. AUDITORIA INICIAL DO AMBIENTE

Antes de implementar:

1. Analise todo o repositório atual.
2. Identifique tecnologias existentes.
3. Identifique scripts.
4. Identifique APIs.
5. Identifique integrações.
6. Identifique arquivos de configuração.
7. Identifique dependências.
8. Identifique credenciais já configuradas, sem expô-las.
9. Identifique código reutilizável.
10. Identifique limitações técnicas.
11. Identifique possíveis gargalos.
12. Identifique tudo o que ainda precisa ser construído.

Não reescreva código existente sem necessidade.

Caso exista uma arquitetura melhor, faça a mudança de maneira incremental e documente a decisão.

Primeiro estabeleça:

```text
CURRENT ARCHITECTURE
        ↓
TARGET ARCHITECTURE
        ↓
IMPLEMENTATION PLAN
```

Depois comece a implementação.

---

# 5. ARQUITETURA AI-NATIVE

A inteligência artificial não deve existir apenas na geração dos vídeos.

Ela deve participar de todo o ciclo:

```text
Research
Trend Detection
Topic Selection
Scriptwriting
Storyboarding
Prompt Engineering
Continuity Management
Quality Analysis
Metadata Generation
Analytics Interpretation
Pattern Detection
Content Strategy
Optimization
```

Sempre que uma tarefa puder ser melhorada por raciocínio de LLM, visão computacional ou análise multimodal, considere incorporá-la à arquitetura.

---

# 6. PESQUISA DE TENDÊNCIAS

Criar um módulo de descoberta de tendências.

O sistema deverá pesquisar fontes públicas e APIs permitidas, como:

* YouTube;
* YouTube Shorts;
* Google Trends;
* mecanismos de busca;
* notícias;
* Reddit;
* outras fontes públicas relevantes;
* APIs oficiais.

Não depender de uma única fonte.

O objetivo é identificar assuntos com:

* aumento recente de interesse;
* grande volume de visualizações;
* alto engajamento;
* crescimento acelerado;
* forte curiosidade;
* relevância para o público americano;
* potencial de retenção;
* capacidade de ser adaptado para menos de 40 segundos;
* possibilidade de produzir conteúdo original.

O sistema deverá evitar simplesmente copiar conteúdos existentes.

A tendência serve como sinal para descobrir oportunidades.

---

# 7. VIRALITY SCORE

Criar um mecanismo de pontuação.

Exemplo conceitual:

```text
Virality Score =
    Trend Growth
  + Recent Views
  + Engagement
  + Topic Momentum
  + Curiosity
  + Short-form Suitability
  + US Audience Relevance
  + Originality
  - Saturation
  - Risk
```

Cada tema deverá receber:

```json
{
  "topic": "",
  "category": "",
  "trend_score": 0,
  "viral_potential": 0,
  "us_relevance": 0,
  "competition": 0,
  "shorts_fit": 0,
  "originality": 0,
  "risk": 0,
  "final_score": 0
}
```

Registrar por que cada tema foi selecionado.

Evitar automaticamente:

* assuntos excessivamente saturados;
* temas que precisam de contexto longo;
* temas difíceis de explicar em 40 segundos;
* assuntos com risco de desinformação;
* conteúdos com alto risco de copyright;
* conteúdos potencialmente perigosos;
* assuntos com alto risco de monetização.

---

# 8. SELEÇÃO AUTOMÁTICA DO TEMA

O sistema deve pesquisar múltiplos candidatos e escolher automaticamente o melhor.

Não perguntar ao operador qual tema deve ser usado, salvo quando a configuração definir explicitamente seleção manual.

O tema deve ser selecionado por dados.

---

# 9. PESQUISA PROFUNDA DO TEMA

Depois de selecionar um tema:

1. Pesquisar o assunto.
2. Verificar fatos.
3. Identificar contexto.
4. Identificar informações interessantes.
5. Identificar ângulos pouco explorados.
6. Identificar possíveis hooks.
7. Identificar riscos.
8. Identificar elementos que geram curiosidade.
9. Identificar a melhor forma de apresentar o assunto em até 40 segundos.

Sempre priorizar conteúdo original.

Não copiar scripts de terceiros.

---

# 10. ROTEIRO

Gerar o roteiro final em **American English**.

O roteiro deve ser pensado especificamente para Shorts.

Estrutura sugerida:

```text
0s–2s
HOOK

2s–8s
SETUP

8s–16s
ESCALATION

16s–24s
REVELATION

24s–32s
PAYOFF

32s–40s
ENDING / LOOP / CTA
```

Essa estrutura é apenas uma referência.

Adaptar de acordo com o tema.

O roteiro deve possuir:

* hook forte;
* linguagem natural americana;
* frases curtas;
* ritmo rápido;
* progressão narrativa;
* curiosidade;
* payoff;
* conclusão;
* possibilidade de loop;
* ausência de trechos desnecessários.

Não adicionar CTA apenas por adicionar.

Caso o CTA prejudique a retenção, evitar.

---

# 11. ESTRUTURA TEMPORAL DO VÍDEO

O sistema deve tratar o vídeo como uma linha temporal contínua.

Exemplo:

```text
00.0 → 02.0
Hook

02.0 → 08.0
Setup

08.0 → 16.0
Escalation

16.0 → 24.0
Reveal

24.0 → 32.0
Payoff

32.0 → 40.0
Ending
```

Cada decisão visual, narrativa e sonora deve estar associada ao tempo.

---

# 12. DIVISÃO EM 5 SEGMENTOS

O Veo 3.1 Lite gera aproximadamente **8 segundos por vídeo**.

Portanto, um Short de aproximadamente 40 segundos será construído assim:

```text
SEGMENT 1 = 0–8s
SEGMENT 2 = 8–16s
SEGMENT 3 = 16–24s
SEGMENT 4 = 24–32s
SEGMENT 5 = 32–40s
```

Esses segmentos NÃO devem ser tratados como cinco vídeos independentes.

Eles devem ser tratados como:

```text
ONE CONTINUOUS VIDEO
```

dividido em cinco gerações.

---

# 13. STORYBOARD

Cada segmento deve possuir:

```json
{
  "segment": 1,
  "duration": 8,
  "purpose": "",
  "visual_description": "",
  "camera": "",
  "lens": "",
  "lighting": "",
  "characters": "",
  "environment": "",
  "objects": "",
  "action": "",
  "narration": "",
  "dialogue": "",
  "sound_design": "",
  "transition_to_next": "",
  "continuity_state": ""
}
```

O storyboard deve descrever não apenas cada segmento, mas também como ele se conecta ao próximo.

---

# 14. CONTINUIDADE ENTRE SEGMENTOS

Essa é uma das prioridades máximas do projeto.

Os cinco segmentos devem parecer uma única filmagem contínua.

Preservar:

* personagens;
* aparência;
* idade aparente;
* roupas;
* cabelo;
* acessórios;
* cenário;
* objetos;
* posição dos objetos;
* iluminação;
* horário aparente;
* clima;
* paleta de cores;
* câmera;
* lente;
* enquadramento;
* movimento da câmera;
* direção do movimento;
* velocidade;
* voz;
* narrador;
* sotaque;
* estilo;
* ritmo.

Nunca trocar arbitrariamente:

```text
character
clothing
voice
camera
lighting
environment
color
```

de um segmento para outro.

---

# 15. CONTINUITY BIBLE

Criar automaticamente um documento interno:

```text
CONTINUITY_BIBLE
```

Ele deverá armazenar:

```text
Characters
Appearance
Clothing
Hair
Accessories
Environment
Lighting
Color Palette
Camera
Lens
Camera Movement
Objects
Object Positions
Actions
Voice
Narrator
Accent
Audio Style
Visual Style
Temporal State
Current Scene State
Previous Scene Ending
Next Scene Starting State
```

A Continuity Bible deve ser reutilizada em todos os prompts.

---

# 16. CONTINUIDADE EXATA

Exemplo:

Se o segmento 1 termina:

```text
Character standing beside a red door,
right hand touching the handle,
door opened 20 degrees,
camera behind the character,
warm light coming from inside.
```

O segmento 2 deverá começar exatamente nesse estado:

```text
Character still standing beside the same red door,
right hand still on the handle,
door continuing from approximately 20 degrees open,
same camera position,
same warm lighting,
same environment.

Continue the previous action.
Do NOT restart the scene.
```

Nunca reiniciar uma ação já iniciada.

---

# 17. PROMPTS PARA VEO 3.1 LITE

Criar prompts extremamente detalhados.

Cada prompt deverá possuir:

```text
SCENE CONTEXT
CHARACTER CONTINUITY
ENVIRONMENT
OBJECT CONTINUITY
ACTION
CAMERA
LENS
LIGHTING
COLOR
MOTION
AUDIO
DIALOGUE / NARRATION
TIMING
CONTINUITY REQUIREMENTS
NEGATIVE CONSTRAINTS
```

O prompt do segmento seguinte deve receber o estado final do segmento anterior.

Exemplo:

```text
Previous segment final state:
- character standing 1 meter from the door
- right hand touching handle
- camera behind left shoulder
- warm indoor lighting
- door opening 30 degrees
- character looking toward hallway

Continue EXACTLY from this state.
```

---

# 18. GERAÇÃO DOS SEGMENTOS

Criar um sistema de jobs.

Exemplo:

```text
JOB
 ├── Segment 1
 ├── Segment 2
 ├── Segment 3
 ├── Segment 4
 └── Segment 5
```

O sistema deverá:

1. criar o job;
2. gerar os prompts;
3. enviar requisições;
4. acompanhar o status;
5. baixar os arquivos;
6. validar os arquivos;
7. armazenar os metadados;
8. executar retries;
9. registrar erros;
10. continuar de onde parou.

Não perder jobs devido a falhas temporárias.

---

# 19. VALIDAÇÃO DOS SEGMENTOS

Validar automaticamente:

* duração;
* resolução;
* codec;
* FPS;
* áudio;
* corrupção;
* existência do arquivo;
* orientação;
* proporção;
* volume;
* formato.

Preferência:

```text
1080x1920
9:16
H.264
AAC
```

quando disponível e adequado.

---

# 20. PÓS-PRODUÇÃO

Pipeline:

```text
Veo Segments
      ↓
Normalize
      ↓
Concatenate
      ↓
Narration
      ↓
Sound Effects
      ↓
Background Music
      ↓
Captions
      ↓
Audio Normalization
      ↓
Final Render
```

Resultado:

```text
OneMoreShort_Final.mp4
```

Nunca ultrapassar a duração máxima definida na configuração.

---

# 21. ÁUDIO

Suportar:

* narração;
* música;
* efeitos sonoros;
* ducking automático;
* normalização de volume.

A voz deve permanecer consistente durante o vídeo.

Não trocar narrador.

Não trocar voz.

Não trocar sotaque.

---

# 22. CAPTIONS

Adicionar captions quando fizer sentido.

As legendas devem:

* acompanhar exatamente a fala;
* possuir timing preciso;
* ser fáceis de ler;
* ser adequadas para celulares;
* respeitar safe areas;
* não esconder elementos importantes;
* manter identidade visual consistente.

---

# 23. QUALITY GATE

Antes de publicar:

```text
QUALITY GATE
```

Verificar:

```text
[✓] Duration
[✓] Resolution
[✓] FPS
[✓] Audio
[✓] Narration
[✓] Captions
[✓] Continuity
[✓] No corrupted segment
[✓] Metadata
[✓] Title
[✓] Description
[✓] Hashtags
[✓] Policy checks
[✓] Originality checks
```

Caso falhe:

```text
RETRY
↓
REGENERATE
↓
VALIDATE
```

Até o limite configurado.

---

# 24. TÍTULO E METADADOS

Gerar automaticamente:

* title;
* description;
* hashtags;
* keywords;
* category;
* upload timing;
* pinned comment quando aplicável.

Títulos devem ser:

* curtos;
* naturais;
* curiosos;
* apropriados para o público americano;
* compatíveis com o conteúdo.

Não usar clickbait falso.

---

# 25. THUMBNAIL / FRAME

Preparar automaticamente uma imagem ou frame representativo quando aplicável.

Manter identidade visual do OneMoreShort.

---

# 26. YOUTUBE API

Integrar com a API oficial do YouTube.

Implementar:

* OAuth;
* upload;
* título;
* descrição;
* tags;
* categoria;
* visibilidade;
* agendamento;
* status;
* captura do ID;
* retries;
* tratamento de erros.

Nunca burlar:

* autenticação;
* limites;
* sistemas de segurança;
* políticas;
* verificações;
* restrições da plataforma.

Quando uma etapa exigir ação humana oficial, marcar:

```text
WAITING_FOR_HUMAN_ACTION
```

e explicar:

```text
PROBLEM
ROOT CAUSE
EXACT HUMAN ACTION
NEXT AUTOMATIC STEP
```

Após a autenticação inicial, reutilizar tokens de maneira segura.

---

# 27. PUBLICAÇÃO

A publicação deve ser configurável.

Exemplo:

```yaml
upload:
  enabled: true
  visibility: public

  schedule:
    enabled: true
    timezone: America/Sao_Paulo
```

Suportar:

```text
draft
private
unlisted
scheduled
public
```

Nunca publicar itens marcados:

```text
BLOCKED
FAILED
NEEDS_REVIEW
```

---

# 28. MONETIZAÇÃO

Estudar e implementar o máximo possível do processo de monetização através dos mecanismos oficiais disponíveis.

Nunca tentar burlar requisitos.

Não automatizar ilegalmente:

* identidade;
* verificação;
* contratos;
* aprovação;
* informações financeiras;
* consentimentos;
* processos que exijam ação humana.

Quando necessário:

```text
WAITING_FOR_HUMAN_ACTION
```

O sistema deve registrar o que precisa ser feito e continuar automaticamente depois que a etapa oficial for concluída.

---

# 29. BANCO DE DADOS

Criar uma estrutura para armazenar:

```text
Topics
Trend Data
Research
Scripts
Storyboards
Continuity Bibles
Prompts
Generation Jobs
Video Segments
Final Videos
Metadata
Uploads
YouTube IDs
Analytics
Retention
Engagement
Errors
Retries
Content Insights
```

Relacionamento:

```text
Topic
 ↓
Research
 ↓
Script
 ↓
Storyboard
 ↓
Continuity Bible
 ↓
Generation Job
 ↓
Segments
 ↓
Final Video
 ↓
Upload
 ↓
Analytics
 ↓
Content Intelligence
 ↓
Future Strategy
```

Cada produção deverá possuir um ID único.

Exemplo:

```text
OMS-20260907-0001
```

---

# 30. SISTEMA DE JOBS

Estados:

```text
DISCOVERING
↓
SELECTED
↓
RESEARCHING
↓
SCRIPTING
↓
STORYBOARDING
↓
GENERATING
↓
VALIDATING
↓
EDITING
↓
QUALITY_CHECK
↓
READY
↓
UPLOADING
↓
PUBLISHED
↓
ANALYZING
↓
LEARNED
```

Estados de erro:

```text
FAILED
RETRYING
BLOCKED
NEEDS_HUMAN_ACTION
```

O sistema deve ser **idempotente**.

Se for interrompido no meio, deve continuar do ponto correto.

---

# 31. OBSERVABILIDADE

Logs estruturados deverão registrar:

```text
timestamp
job_id
stage
action
duration
status
error
retry_count
API
cost
```

Métricas operacionais:

```text
videos generated
videos published
generation success rate
failure rate
average generation time
average cost/video
API errors
upload failures
```

---

# 32. CONTROLE DE CUSTOS

Implementar limite diário.

Exemplo:

```yaml
limits:
  daily_budget_usd: 10
  max_video_generation_retries: 3
  max_api_retries: 5
  max_videos_per_day: 1
```

Nunca permitir loops infinitos de geração.

Caso o orçamento seja atingido:

```text
PAUSE_PIPELINE
```

Registrar o motivo.

---

# 33. ANALYTICS DE CADA VÍDEO

Esta parte é FUNDAMENTAL.

Cada vídeo publicado deverá possuir um registro independente de performance.

O sistema deve coletar periodicamente, através de APIs e ferramentas oficiais disponíveis, métricas como:

* views;
* engaged views;
* alcance / audiência alcançada, quando disponível;
* likes;
* comentários;
* compartilhamentos;
* inscritos ganhos;
* watch time;
* average view duration;
* average percentage viewed;
* audience retention;
* visualizações completas;
* taxa de abandono;
* relação entre views e engajamento;
* performance inicial;
* performance nas primeiras horas;
* performance em 24 horas;
* performance em 48 horas;
* performance em 7 dias;
* velocidade de crescimento;
* fontes de tráfego, quando disponível;
* novos espectadores vs. recorrentes, quando disponível;
* visualização vs. deslize, quando disponível.

Não analisar somente views.

---

# 34. CURVA DE RETENÇÃO

Registrar a retenção ao longo do tempo.

Exemplo:

```text
0s
2s
4s
6s
8s
10s
15s
20s
25s
30s
35s
40s
```

Exemplo:

```text
0s  → 100%
2s  → 94%
4s  → 89%
8s  → 83%
15s → 74%
20s → 69%
25s → 66%
30s → 61%
35s → 58%
40s → 55%
```

Detectar quedas.

Exemplo:

```text
8s → 83%
10s → 65%
```

Interpretar isso como possível problema naquele trecho.

O sistema deve tentar identificar:

```text
qual cena causou a queda
qual frase causou a queda
qual mudança visual causou a queda
qual transição causou a queda
```

quando os dados permitirem.

---

# 35. ANÁLISE DO HOOK

O sistema deve analisar os primeiros segundos de cada vídeo.

Categorizar automaticamente o hook:

```text
Question
Shock
Curiosity
Unexpected Fact
Story
Conflict
Mystery
Prediction
Contrarian Statement
```

Comparar:

```text
Hook Type
Average Retention
Average Views
Share Rate
Subscriber Conversion
```

Descobrir quais hooks funcionam melhor.

---

# 36. ANÁLISE DA ESTRUTURA

Associar cada vídeo às suas características:

```text
Topic
Category
Hook Type
Narrative Structure
Video Duration
Number of Scenes
Visual Style
Narrator
Voice Style
Pacing
Caption Style
Ending Type
Loop Used
CTA Used
```

Comparar essas características com os resultados.

Exemplo:

```text
Curiosity Hook
Average retention: 78%

Question Hook
Average retention: 61%

Shock Hook
Average retention: 84%
```

---

# 37. ANÁLISE DE ENGAJAMENTO

Calcular indicadores derivados:

```text
Like Rate
Comment Rate
Share Rate
Subscriber Conversion
Engagement Rate
View-to-Like Ratio
View-to-Subscriber Ratio
```

Exemplo:

```text
1,000,000 views
45,000 likes
2,100 comments
8,000 shares
12,000 subscribers
```

Calcular:

```text
Like Rate
Comment Rate
Share Rate
Subscriber Conversion
```

---

# 38. ANÁLISE TEMPORAL

Acompanhar a velocidade de crescimento.

Exemplo:

```text
10 min  → 500 views
30 min  → 3,000 views
1 hour  → 12,000 views
3 hours → 85,000 views
6 hours → 310,000 views
24 hours → 1,200,000 views
```

Classificar:

```text
Dead
Slow Growth
Normal
Accelerating
Viral
Explosive
```

---

# 39. COMPARAÇÃO ENTRE VÍDEOS

Nunca analisar um vídeo isoladamente.

Comparar cada vídeo contra:

* média do canal;
* mediana do canal;
* últimos 5 vídeos;
* últimos 10 vídeos;
* vídeos da mesma categoria;
* vídeos com estrutura semelhante;
* melhores vídeos;
* piores vídeos.

Exemplo:

```text
VIDEO #42

Views:
+340% vs channel average

Retention:
+18% vs channel average

Like Rate:
+27% vs channel average

Shares:
+190% vs channel average
```

---

# 40. DETECÇÃO DE PADRÕES VIRAIS

Quando um vídeo apresentar desempenho excepcional, descobrir o que pode ter contribuído para isso.

Exemplo:

```text
Viral Video

Topic:
Unexpected technology fact

Hook:
Contrarian statement

Duration:
34 seconds

Average retention:
91%

Completion:
78%

Share rate:
2.4%

Ending:
Loop

Visual:
Fast cinematic sequence
```

O sistema deverá extrair conhecimento desses padrões.

---

# 41. CONTENT INTELLIGENCE

Criar uma camada chamada:

```text
CONTENT_INTELLIGENCE
```

Responsável por responder continuamente:

```text
What topics work?
What hooks work?
What video lengths work?
What pacing works?
What visual styles work?
What endings work?
What narration styles work?
What topics generate shares?
What topics generate subscribers?
What topics generate retention?
What topics fail?
Why do they fail?
```

---

# 42. FEEDBACK LOOP

Os resultados dos vídeos devem voltar automaticamente para a pipeline.

Fluxo:

```text
RESEARCH
   ↓
SCRIPT
   ↓
VIDEO
   ↓
PUBLISH
   ↓
ANALYTICS
   ↓
RETENTION ANALYSIS
   ↓
CONTENT INTELLIGENCE
   ↓
NEW INSIGHTS
   ↓
BETTER RESEARCH
   ↓
BETTER SCRIPT
   ↓
BETTER VIDEO
```

O sistema deve aprender continuamente.

Ele não deve simplesmente publicar mais.

Ele deve tentar publicar **melhor**.

---

# 43. TRÊS NÍVEIS DE SUCESSO

Não usar apenas views para avaliar sucesso.

Avaliar cada vídeo em três níveis:

## 1. RETENÇÃO

A pessoa continuou assistindo?

Métricas:

```text
Average Percentage Viewed
Average View Duration
Completion
Retention Curve
Drop-off Points
```

## 2. ENGAJAMENTO

A pessoa interagiu?

Métricas:

```text
Likes
Comments
Shares
Engagement Rate
```

## 3. CONVERSÃO

A pessoa quis acompanhar o canal?

Métricas:

```text
Subscribers Gained
Subscriber Conversion
Returning Viewers
```

Um Short com muitas views mas pouca conversão não deve necessariamente ser tratado como um sucesso completo.

---

# 44. RELATÓRIO AUTOMÁTICO POR VÍDEO

Para cada vídeo publicar um relatório interno:

```text
ONE MORE SHORT
VIDEO PERFORMANCE REPORT

Video:
"The Strange Reason..."

Views:
1,240,832

Average Percentage Viewed:
87%

Average View Duration:
34.8s

Likes:
62,401

Comments:
3,842

Shares:
9,214

Subscribers:
8,104

Retention:
Excellent

Hook:
Excellent

Engagement:
Above Average

Virality Score:
94/100
```

Depois:

```text
WHAT WORKED

1. Strong curiosity hook
2. High retention in first 10 seconds
3. Unexpected payoff
4. Strong shareability
5. Short 35-second runtime
```

E:

```text
WHAT FAILED

1. Retention dropped at 27 seconds
2. CTA reduced momentum
3. Ending could create a stronger loop
```

E finalmente:

```text
NEXT VIDEO RECOMMENDATION

Use:
- same hook style
- similar pacing
- similar runtime
- stronger payoff
- no interruption before ending
```

Essas conclusões devem ser armazenadas no banco de dados.

---

# 45. APRENDIZADO DA FÁBRICA

O sistema deve identificar continuamente:

```text
Best Topics
Best Categories
Best Hooks
Best Durations
Best Narrative Structures
Best Visual Styles
Best Voices
Best Pacing
Best Caption Styles
Best Endings
Best Loop Structures
Best CTAs
```

Também identificar:

```text
Worst Topics
Worst Hooks
Worst Structures
Worst Durations
Worst Visual Styles
Common Drop-off Points
Common Failure Patterns
```

---

# 46. ESTRATÉGIA ADAPTATIVA

Com base nos dados:

Se:

```text
Topic A
→ strong retention
→ high shares
→ high subscriber conversion
```

a probabilidade de selecionar tópicos semelhantes deverá aumentar.

Se:

```text
Topic B
→ weak retention
→ low engagement
→ low conversion
```

sua prioridade deverá diminuir.

Entretanto, não criar um sistema que fique preso em um único tema.

Usar exploração + exploração de vencedores.

Exemplo conceitual:

```text
70% proven formats
30% experimentation
```

Essa proporção deve ser configurável.

---

# 47. A/B TESTING

Quando aplicável, permitir testar:

```text
Hook A
vs
Hook B
```

ou:

```text
Ending A
vs
Ending B
```

ou:

```text
Caption Style A
vs
Caption Style B
```

O sistema deverá medir diferenças de performance.

Não duplicar conteúdo de maneira que viole políticas da plataforma.

---

# 48. SISTEMA DE CONHECIMENTO

Criar uma base de conhecimento interna contendo:

```text
Successful Topics
Successful Hooks
Successful Scripts
Successful Structures
Successful Prompts
Successful Visual Styles
Successful Endings
Failed Experiments
Analytics Insights
```

A cada vídeo novo:

```text
READ PREVIOUS KNOWLEDGE
        ↓
CREATE NEW VIDEO
        ↓
PUBLISH
        ↓
OBSERVE
        ↓
UPDATE KNOWLEDGE
```

---

# 49. ARQUITETURA DE ARQUIVOS

Criar estrutura semelhante a:

```text
one-more-short/
│
├── app/
│   ├── research/
│   ├── trends/
│   ├── scripting/
│   ├── storyboard/
│   ├── continuity/
│   ├── veo/
│   ├── audio/
│   ├── editing/
│   ├── captions/
│   ├── youtube/
│   ├── analytics/
│   ├── intelligence/
│   └── pipeline/
│
├── config/
│
├── database/
│
├── jobs/
│
├── storage/
│   ├── research/
│   ├── scripts/
│   ├── storyboards/
│   ├── continuity/
│   ├── prompts/
│   ├── segments/
│   ├── renders/
│   ├── published/
│   └── analytics/
│
├── logs/
│
├── tests/
│
├── scripts/
│
├── .env.example
├── .gitignore
├── README.md
├── ARCHITECTURE.md
├── SETUP.md
├── API.md
├── PIPELINE.md
├── OPERATIONS.md
└── TROUBLESHOOTING.md
```

Adapte à stack existente quando necessário.

---

# 50. SEGURANÇA

Nunca colocar diretamente no código:

* API keys;
* OAuth secrets;
* tokens;
* senhas;
* credenciais financeiras.

Utilizar:

```text
.env
environment variables
Secret Manager
```

quando apropriado.

Nunca versionar credenciais.

---

# 51. CONFIABILIDADE

Toda integração externa deverá ter:

* timeout;
* retry;
* exponential backoff;
* rate limit handling;
* logs;
* tratamento de erros;
* idempotência;
* circuit breaker quando fizer sentido.

Não assumir que nenhuma API falhará.

---

# 52. DASHBOARD

Criar posteriormente um dashboard para mostrar:

```text
Pipeline Status
Current Jobs
Videos Generated
Videos Published
Failed Jobs
Daily Cost
Trending Topics
Recent Videos
Performance
Retention
Engagement
Subscribers
Top Videos
Worst Videos
Content Insights
```

Não priorizar dashboard antes da pipeline principal estar funcionando.

---

# 53. TESTES

Criar:

* unit tests;
* integration tests;
* pipeline tests;
* API mocks;
* failure recovery tests.

Testar:

```text
Research
Topic Ranking
Script Generation
Storyboard
Continuity Bible
Prompt Generation
Veo Job
Video Validation
Editing
Audio
Captions
Upload
Retry
Database
Analytics
Content Intelligence
Failure Recovery
```

Simular:

```text
Veo API timeout
YouTube API timeout
Corrupted video
Missing segment
Invalid audio
Database unavailable
Network failure
OAuth expiration
Rate limit
```

O sistema deve se recuperar automaticamente sempre que possível.

---

# 54. PRIMEIRO TESTE REAL

Depois que a infraestrutura estiver funcionando, execute um teste completo de produção.

O tema NÃO deverá ser escolhido manualmente.

Executar:

```text
Pesquisar tendências atuais
        ↓
Analisar candidatos
        ↓
Escolher automaticamente
        ↓
Pesquisar profundamente
        ↓
Criar roteiro
        ↓
Criar storyboard
        ↓
Criar Continuity Bible
        ↓
Criar 5 prompts
        ↓
Gerar 5 segmentos
        ↓
Validar
        ↓
Editar
        ↓
Adicionar áudio
        ↓
Adicionar captions
        ↓
Quality Gate
        ↓
Gerar título
        ↓
Gerar descrição
        ↓
Publicar
        ↓
Registrar YouTube ID
        ↓
Começar coleta de analytics
```

---

# 55. OPERAÇÃO DIÁRIA

O sistema deverá ser preparado para uma rotina semelhante a:

```text
DAILY JOB
    ↓
Trend Research
    ↓
Topic Selection
    ↓
Content Production
    ↓
Quality Gate
    ↓
Publishing
    ↓
Analytics Tracking
    ↓
Learning
```

O horário deverá ser configurável.

---

# 56. AUTONOMIA

O sistema deverá funcionar sem interação humana durante todas as etapas que puderem ser automatizadas legal e tecnicamente.

Não solicitar confirmação para decisões técnicas triviais.

Quando existirem duas opções razoáveis:

1. escolher a melhor;
2. implementar;
3. documentar a decisão.

Somente interromper quando for realmente necessário por:

* autenticação;
* autorização;
* pagamento;
* aprovação;
* identidade;
* configuração de conta;
* requisitos legais;
* ação obrigatória da plataforma;
* acesso indisponível.

---

# 57. PRINCÍPIOS DE CONTEÚDO

Todo conteúdo deverá:

* ser original;
* ser em American English;
* buscar adequação à monetização;
* evitar desinformação;
* evitar copiar criadores;
* evitar reutilizar vídeos de terceiros sem autorização;
* evitar problemas de copyright;
* evitar manipulação enganosa;
* respeitar políticas das plataformas;
* priorizar retenção e valor ao espectador.

---

# 58. IDENTIDADE DA MARCA

Marca:

**OneMoreShort**

Características:

```text
Fast
Viral
Modern
Bold
Internet-native
Energetic
Recognizable
Clean
```

Criar consistência visual e narrativa entre os vídeos.

---

# 59. PRINCÍPIO DE DECISÃO

Prioridade:

```text
1. Safety
2. Compliance
3. Reliability
4. Originality
5. Retention
6. Quality
7. Automation
8. Cost
9. Scale
```

---

# 60. MÉTRICA MAIS IMPORTANTE

Não pensar somente:

```text
"How many views did this video get?"
```

Pensar:

```text
"Why did this video perform this way?"
```

E depois:

```text
"How can the next video perform better?"
```

Cada vídeo publicado deve contribuir para melhorar a estratégia do próximo.

---

# 61. OBJETIVO FINAL

O objetivo não é criar um simples gerador de vídeos.

O objetivo é criar uma **fábrica autônoma de conteúdo que pesquisa, cria, produz, valida, publica, mede, aprende e melhora continuamente**.

O sistema final deverá funcionar conceitualmente assim:

```text
             ┌──────────────────┐
             │   TREND RESEARCH │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │ TOPIC SELECTION  │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │    SCRIPT AI     │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │   STORYBOARD AI  │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │  CONTINUITY AI   │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │    VEO 3.1      │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │ VIDEO PRODUCTION │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │   QUALITY GATE   │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │     YOUTUBE      │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │     ANALYTICS    │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │    RETENTION     │
             │     ANALYSIS     │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │    CONTENT       │
             │  INTELLIGENCE    │
             └────────┬─────────┘
                      ↓
             ┌──────────────────┐
             │  BETTER NEXT     │
             │      VIDEO       │
             └──────────────────┘
```

---

# 62. EXECUÇÃO

Agora execute o projeto.

Comece pela auditoria do ambiente.

Depois:

```text
1. Defina a arquitetura
2. Documente as decisões
3. Estruture o projeto
4. Configure dependências
5. Implemente os módulos
6. Implemente a pipeline
7. Implemente testes
8. Execute os testes
9. Corrija falhas
10. Integre as APIs
11. Execute uma produção completa
12. Publique o primeiro Short quando as integrações oficiais estiverem disponíveis
13. Inicie a coleta de analytics
14. Implemente Content Intelligence
15. Conecte analytics ao processo de criação
16. Prepare a execução diária
```

Não fique apenas descrevendo o que deveria ser feito.

**FAÇA A IMPLEMENTAÇÃO.**

Quando encontrar um problema:

1. tente resolver automaticamente;
2. valide a correção;
3. continue o fluxo.

Somente solicitar intervenção humana quando realmente necessário.

Quando isso ocorrer, registrar:

```text
PROBLEM
ROOT CAUSE
WHAT WAS AUTOMATED
WHAT REMAINS
EXACT HUMAN ACTION REQUIRED
NEXT AUTOMATIC STEP
```

O resultado final deve ser uma infraestrutura capaz de transformar:

```text
TREND
→ IDEA
→ SCRIPT
→ STORYBOARD
→ 5 CONTINUOUS VEO SEGMENTS
→ FINAL SHORT
→ PUBLICATION
→ ANALYTICS
→ RETENTION ANALYSIS
→ CONTENT INTELLIGENCE
→ BETTER CONTENT
```

com o mínimo possível de intervenção humana.


