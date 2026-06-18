# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project overview

BIIA (bibliografia + ia) is a single-file browser app (`index.html`) for AI-assisted classification of academic literature. It takes a CSV of papers, applies user-defined classification rules via regex and/or the Gemini API, and exports an enriched CSV. No build step, no dependencies, no server — the entire application is one HTML file deployed to GitHub Pages.

## Running locally

Open `index.html` directly in a browser, or use any static file server:

```
npx serve .
# or
python -m http.server
```

There are no install steps, build commands, or test suites.

## Architecture

Everything lives in `index.html` as a single `<script>` block. The file has no modules, bundler, or external JS — all logic is plain vanilla JS inline.

**Data flow:**
1. User loads a CSV → `parseCSV()` → `allRows[]` (array of row objects keyed by CSV headers)
2. User defines rules in `userRules[]` (each rule has: `id`, `method`, `inputCols`, `regexText`, `prompt`, `mode`, `active`)
3. On "Classificar": regex phase runs synchronously across all rows; AI phase runs all rules in parallel via `Promise.all(aiRules.map(runAIRule))`
4. Results written back into `allRows[i][rule.id]` and `allRows[i][rule.id + "_source"]`
5. Download re-serializes `allRows` to CSV

**Classification pipeline (`startClassification`):**
- Phase 1 (regex): for each `regex` or `regex+ai` rule, `applyRuleRegex()` tests each row synchronously; matches written immediately
- Phase 2 (AI): each `ai` or `regex+ai` rule spawns an independent async stream (`runAIRule`); rows empty after the regex phase are batched in groups of 5 (`BATCH = 5`) and sent to Gemini; 6-second pause between batches; `runWithBackoff()` wraps each batch with automatic retry (2 min wait for attempts 1–3, 5 min for 4+). During the wait, `setPhaseRetry()` shows a per-column countdown (`⚠️ tentativa N · mm:ss`) with a manual **retry** button; clicking it calls `skipBackoffWait(phaseId)` (sets `skipWait[phaseId] = true`), which breaks the countdown loop early and triggers the next attempt immediately. Classification can also be paused at any time via `pauseClassification()` (`stopFlag`)

**Model selection (`callModel`):**
- `pinnedModel`: user-selected model from the dropdown, stored in `localStorage` as `biia_pinned_model`
- `activeModel`: last model that responded successfully, stored as `biia_model`
- Auto mode: tries models in `GEMINI_MODELS` order until one succeeds

**Persistence (localStorage keys):**
- `biia_gemini_key` — API key
- `biia_model` — last successful model
- `biia_pinned_model` — user-pinned model selection
- `biia_rules_v1` — `userRules[]` serialized as `{v:1, rules:[...]}`
- `biia_rulelib_v1` — `ruleLibrary[]` (user-saved reusable rules), same schema

**UI rendering:** all UI is imperative DOM manipulation (innerHTML strings). `buildRulesUI()` re-renders the entire rules list; `renderTable()` re-renders the results table (capped at 300 visible rows); `updateStats()` re-renders the filter pills. No virtual DOM or framework.

**Prompt construction (`buildPromptForRule`):** each AI rule receives its own independent prompt containing only the columns configured for that rule. The model is asked to respond with a JSON array `[{"index": N, "<rule.id>": "value"}]`. Parsing handles both valid JSON and partial/malformed responses via regex fallback.

**Color system:** CSS custom properties map each taxonomy value to a foreground color + background color (e.g., `--arch-t` / `--arch-t-bg` for Transformer). `badgeCss(colId, value)` maps rule ID + value to a CSS class. The `architecture` column is treated specially throughout: its values are comma-separated multi-tags, and the stats pills and table badges split on commas before lookup.

## Key design constraints

- The regex phase is conservative by design — it only matches on `Title` and `Author Keywords`, not the abstract. Terms in the abstract frequently appear as context rather than as the paper's primary contribution, reducing precision.
- Regex rules are ordered; the first match wins. The task preset deliberately tests `otimização` before `previsão` because optimization papers often mention forecasting as a subcomponent.
- The architecture taxonomy uses atomic, combinable tags — a paper can have multiple tags (e.g., `"Transformer, Rede Recorrente"`). Metaheuristics and training paradigms (PSO, transfer learning) are not architecture tags; they belong in `complementary_technique`.
- The `mode` field per rule controls whether already-filled cells are skipped (`"empty"`) or overwritten (`"all"`), enabling resumable sessions.

## Deployment

Deployed automatically to GitHub Pages from `main` branch. The live URL is `https://tathianamb.github.io/biia/`. No CI configuration exists — a push to `main` is sufficient.

---

## Documentação científica / Scientific documentation

> Esta seção contém os parâmetros completos de reprodutibilidade da ferramenta conforme aplicada na revisão sistemática sobre previsão de energia eólica. Destina-se a subsidiar a seção de Metodologia de artigos científicos.
>
> *This section contains the full reproducibility parameters of the tool as applied in the systematic review on wind energy forecasting. It is intended to support the Methods section of scientific papers.*

---

### Contexto de aplicação / Application context

BIIA foi desenvolvida no contexto de uma revisão sistemática da literatura sobre **previsão de energia eólica** (wind energy forecasting). A ferramenta é agnóstica ao domínio — qualquer conjunto de regras pode ser definido — mas os presets embarcados e a taxonomia descritos abaixo foram projetados especificamente para classificar artigos nesse campo.

*BIIA was developed in the context of a systematic literature review on **wind energy forecasting**. The tool is domain-agnostic, but the built-in presets and taxonomy described below were designed specifically to classify papers in this field.*

---

### Pipeline de classificação / Classification pipeline

A classificação ocorre em duas fases sequenciais:

```
Fase 1 — Regex (síncrona, sem chamadas de API)
  └─ Aplicada a todas as regras configuradas como "regex" ou "regex+ai"
  └─ Artigos sem correspondência ficam vazios → enviados à Fase 2

Fase 2 — IA (paralela)
  └─ Uma stream independente por regra configurada como "ai" ou "regex+ai"
  └─ Todas as streams correm concorrentemente (Promise.all)
  └─ Cada regra usa apenas as linhas ainda vazias após a Fase 1
```

*Classification occurs in two sequential phases: (1) a synchronous regex pass with no API calls, followed by (2) parallel independent AI streams, one per active AI rule, each processing only rows left empty after the regex phase.*

---

### Parâmetros de inferência da IA / AI inference parameters

Os seguintes parâmetros foram utilizados em todas as chamadas de API durante a revisão:

| Parâmetro | Valor |
|-----------|-------|
| Provider | Google Gemini API (v1beta) |
| Modelos testados (ordem de fallback) | `gemini-3.1-flash-lite`, `gemma-4-31b-it`, `gemma-4-26b-a4b-it` |
| `temperature` | `0` |
| `maxOutputTokens` | `2048` |
| Tamanho do lote (*batch size*) | 5 artigos por requisição |
| Intervalo entre lotes | 6 segundos |
| Retry — tentativas 1–3 | aguarda 2 minutos |
| Retry — tentativa 4+ | aguarda 5 minutos |
| Formato de resposta solicitado | JSON array: `[{"index": N, "<campo>": "valor"}]` |

*The table above lists all inference parameters used for every API call during the review. Temperature 0 was chosen to maximize determinism; batch size of 5 and the inter-batch pause of 6 s were set to stay within the free-tier rate limit of 15 requests per minute.*

---

### Dimensões de classificação / Classification dimensions

Cinco dimensões são classificadas por artigo. As colunas `target` e `task` usam regex+IA; as demais usam apenas IA.

*Five dimensions are classified per paper. `target` and `task` use regex+AI; the remaining three use AI only.*

#### 1. `target` — Variável alvo / Target variable

Método: `regex+ai` | Entradas: `Title`, `Author Keywords`

| Valor | Definição |
|-------|-----------|
| `velocidade do vento` | O modelo proposto tem velocidade do vento como variável de saída |
| `potência` | O modelo tem potência como variável de saída (qualquer fonte) e não se enquadra na regra anterior |
| `outro` | Outra variável de saída, sem modelo proposto claro, ou não aplicável |

**Hierarquia de prioridade regex (primeira correspondência vence):**

| Prioridade | Padrão | Valor atribuído |
|-----------|--------|----------------|
| 1 | `/wind speed/i` | `velocidade do vento` |
| 2 | `/wind power/i` | `potência` |
| — | *(sem correspondência)* | vazio → Fase 2 (IA) |

**Decisões de design:** Apenas `wind power` é usado para `potência`; termos mais amplos como `power output` ou `power generation` geram falsos positivos em artigos que discutem potência como contexto, não como alvo de previsão.

---

#### 2. `task` — Tarefa principal / Primary task

Método: `regex+ai` | Entradas: `Title`, `Author Keywords`

| Valor | Definição |
|-------|-----------|
| `previsão` | Forecasting de velocidade do vento, potência ou variáveis meteorológicas |
| `otimização` | Scheduling, despacho, armazenamento, leilão, gestão de rede |
| `avaliação de recurso` | Avaliação de potencial eólico, ajuste Weibull, análise de sítio |
| `controle` | Wake control, pitch control, controle de frequência |
| `modelagem de curva` | Power curve modeling |
| `detecção de anomalias` | Detecção de outliers, falhas, limpeza de dados SCADA |
| `geração de dados` | Data augmentation, geração de dados sintéticos |
| `simulação física` | CFD, WRF, LES como modelo principal |
| `avaliação de risco` | Risk assessment, quantificação de incerteza como foco principal |
| `revisão` | Revisão sistemática, survey, benchmark, estudo comparativo |
| `outro` | Não se enquadra nas categorias anteriores |

**Hierarquia de prioridade regex (primeira correspondência vence):**

| Prioridade | Padrões | Valor atribuído |
|-----------|---------|----------------|
| 1 | `/systematic review/i`, `/literature survey/i` | `revisão` |
| 2 | `/\bCFD\b/`, `/\bLES\b/`, `/\bWRF\b/` | `simulação física` |
| 3 | `/anomaly detection/i`, `/fault detection/i`, `/fault diagnosis/i` | `detecção de anomalias` |
| 4 | `/data augmentation/i`, `/synthetic data/i` | `geração de dados` |
| 5 | `/risk assessment/i` | `avaliação de risco` |
| 6 | `/wake control/i`, `/pitch control/i`, `/frequency control/i` | `controle` |
| 7 | `/power curve/i` | `modelagem de curva` |
| 8 | `/resource assessment/i`, `/wind potential/i` | `avaliação de recurso` |
| 9 | `/\bscheduling\b/i`, `/\bdispatch\b/i`, `/\barbitrage\b/i`, `/unit commitment/i` | `otimização` |
| 10 | `/forecasting/i`, `/prediction/i` | `previsão` |
| — | *(sem correspondência)* | vazio → Fase 2 (IA) |

**Decisões de design:**
- `otimização` é testada **antes** de `previsão` porque artigos de otimização frequentemente mencionam forecasting como subcomponente; o inverso não ocorre.
- `optimization` sozinho é excluído deliberadamente dos gatilhos de `otimização` por se referir comumente à otimização de hiperparâmetros.
- `SCADA` sozinho é excluído de `detecção de anomalias` pois dados SCADA são usados em múltiplas tarefas, incluindo previsão.
- Os termos são mantidos em até duas palavras para maximizar a taxa de correspondência preservando especificidade.
- Abstract e Index Keywords são excluídos do escopo regex por conterem os termos de disparo frequentemente como contexto, e não como contribuição principal — favorecendo precisão sobre recall, com a API cobrindo os casos restantes.

---

#### 3. `architecture` — Família arquitetural / Architectural family

Método: `ai` | Entradas: `Title`, `Abstract`, `Author Keywords`, `Index Keywords`

Valores são **múltiplos e combináveis** — um artigo pode receber várias tags separadas por vírgula (ex.: `"Transformer, Rede Recorrente"`). Metaheurísticas e paradigmas de treinamento (PSO, transfer learning) **não** são tags de arquitetura; pertencem a `complementary_technique`.

| Tag | Descrição | Exemplos |
|-----|-----------|---------|
| `Transformer` | Backbone baseado em atenção como mecanismo central | Informer, PatchTST, Crossformer, Autoformer, Mamba |
| `Rede Recorrente` | Recorrência temporal explícita com gating | LSTM, GRU, BiLSTM, RNN, Elman, xLSTM |
| `Rede Convolucional` | Extração de features locais via convoluções | CNN, TCN, ResNet, ConvLSTM, WaveNet |
| `Rede de Grafos` | Modelos sobre estruturas de grafo | GCN, GAT, AGCRN, DCRNN, STGCN |
| `MLP-based` | Perceptrons multicamadas com blocos especializados | N-BEATS, N-HiTS, TSMixer, TiDE |
| `Ensemble` | Combinação de múltiplos modelos ou árvores | XGBoost, LightGBM, Random Forest, CatBoost, Stacking |
| `Neuro-Fuzzy` | Inferência fuzzy combinada com redes neurais | ANFIS, FIS+NN |
| `LLM` | Large Language Models adaptados para séries temporais | GPT, LLaMA |
| `Estatístico` | Modelos estatísticos clássicos | ARIMA, SARIMA, regressão, Bayesian DLM |
| `Físico` | Modelos físicos ou de simulação | NWP, WRF, CFD, LES |
| `Outro` | Não classificável nas categorias acima | KAN, Diffusion Models, RL, GAM, Quantum NN |
| `-` | Sem modelo proposto claro | — |

---

#### 4. `model` — Nome do modelo proposto / Proposed model name

Método: `ai` | Entradas: `Title`, `Abstract`, `Author Keywords`, `Index Keywords`

Nome ou sigla **exata** do modelo proposto (ex.: `"DBANN"`, `"CEEMDAN+VMD+GRU"`, `"PINN+Informer"`). Usa `"-"` se não há modelo proposto claro.

---

#### 5. `complementary_technique` — Técnicas complementares / Complementary techniques

Método: `ai` | Entradas: `Title`, `Abstract`, `Author Keywords`, `Index Keywords`

Técnicas complementares à arquitetura principal: otimização de hiperparâmetros, paradigma de treinamento, estratégia metodológica. Exemplos: `"PSO"`, `"NSGA-III feature selection"`, `"transfer learning"`, `"federated learning"`, `"meta-learning"`, `"knowledge distillation"`, `"quantile regression"`, `"Monte Carlo"`. Múltiplos valores separados por vírgula; `"-"` se não aplicável.

---

### Prompts completos / Full prompts

Os prompts abaixo são os exatos enviados à API em cada regra.

*The prompts below are the exact strings sent to the API for each rule.*

#### Prompt — `target`

> Você é um especialista em ML.
> Analise o título e palavras-chave de cada artigo e classifique o campo abaixo:
>
> ━━ target ━━
> Variável alvo do modelo proposto. Siga a HIERARQUIA abaixo em ordem:
> 1. "velocidade do vento": o modelo tem velocidade do vento como variável de saída
> 2. "potência": o modelo tem potência como variável de saída (qualquer fonte: eólica, solar, etc.) e NÃO se enquadra na regra anterior
> 3. "outro": outra variável de saída, sem modelo proposto claro, ou não aplicável

#### Prompt — `task`

> Você é um especialista em ML.
> Analise o título e palavras-chave de cada artigo e classifique o campo abaixo:
>
> ━━ task ━━
> Tarefa principal do artigo. Use EXATAMENTE uma das opções:
> - "previsão": forecasting de velocidade, potência ou variáveis meteorológicas
> - "otimização": scheduling, dispatch, armazenamento, leilão, gestão, feature selection como foco
> - "avaliação de recurso": potencial eólico, Weibull, análise de sítio
> - "controle": wake control, pitch control, controle de frequência
> - "modelagem de curva": power curve modeling
> - "detecção de anomalias": outlier detection, fault detection, limpeza SCADA
> - "geração de dados": data augmentation, synthetic data
> - "simulação física": CFD, WRF, LES como modelo principal
> - "avaliação de risco": risk assessment, uncertainty quantification como foco
> - "revisão": systematic review, survey, benchmark, comparative study
> - "outro": não se encaixa nas anteriores

#### Prompt — `architecture`

> Você é um especialista em ML.
> Analise o título, palavras-chave e abstract de cada artigo e classifique o campo abaixo:
>
> ━━ architecture ━━
> Liste as famílias arquiteturais do modelo PROPOSTO. Podem ser MÚLTIPLAS tags separadas por vírgula.
> Use APENAS as opções abaixo — inclua todas que compõem a arquitetura proposta:
> - "Transformer": backbone baseado em atenção (Transformer, Informer, PatchTST, Mamba, Crossformer, Autoformer)
> - "Rede Recorrente": LSTM, GRU, BiLSTM, RNN, Elman, xLSTM
> - "Rede Convolucional": CNN, TCN, ResNet, ConvLSTM, WaveNet
> - "Rede de Grafos": GCN, GAT, AGCRN, DCRNN, STGCN
> - "MLP-based": N-BEATS, N-HiTS, TSMixer, TiDE
> - "Ensemble": XGBoost, Random Forest, LightGBM, CatBoost, Stacking
> - "Neuro-Fuzzy": sistemas fuzzy + redes neurais (ANFIS, FIS+NN)
> - "LLM": Large Language Models para séries temporais (GPT, LLaMA)
> - "Estatístico": puramente estatístico (ARIMA, SARIMA, regressão, Bayesian DLM)
> - "Físico": puramente físico (NWP, WRF, CFD, LES)
> - "Outro": não classificável (KAN, Diffusion, RL puro, GAM, Quantum NN)
> - "-": sem modelo proposto claro
> REGRAS: Metaheurística e transfer learning NÃO são arquitetura — vão em complementary_technique.

#### Prompt — `model`

> Você é um especialista em ML.
> Analise o título, palavras-chave e abstract de cada artigo e classifique o campo abaixo:
>
> ━━ model ━━
> Nome/sigla EXATA do modelo proposto (ex: "DBANN", "CEEMDAN+VMD+GRU", "PINN+Informer").
> Use "-" se não há modelo proposto claro.

#### Prompt — `complementary_technique`

> Você é um especialista em ML.
> Analise o título, palavras-chave e abstract de cada artigo e classifique o campo abaixo:
>
> ━━ complementary_technique ━━
> Técnicas COMPLEMENTARES à arquitetura: otimização, paradigma de treinamento, estratégia metodológica.
> Exemplos: "PSO", "NSGA-III feature selection", "transfer learning", "federated learning", "meta-learning", "knowledge distillation", "quantile regression", "Monte Carlo".
> Use "-" se não há técnica complementar relevante. Múltiplas separadas por vírgula.

---

### Formato de requisição à API / API request format

Cada batch é enviado no seguinte formato (após o prompt de instrução):

```
Responda APENAS com JSON válido, sem markdown:
[{"index":0,"<campo>":"..."}]

Artigos:
[0]
Title: <título>
Author Keywords: <palavras-chave>

---

[1]
Title: <título>
Author Keywords: <palavras-chave>
```

*Each batch is sent with the instruction prompt followed by the request above. The model is instructed to respond with valid JSON only, no markdown wrappers.*

---

### Rastreabilidade da fonte / Source provenance

Para cada regra configurada como `regex` ou `regex+ai`, uma coluna adicional `<id>_source` é gerada no CSV de saída, registrando se o valor foi atribuído por `"regex"` ou `"ai"`. Isso permite auditar a taxa de cobertura de cada fase por dimensão.

*For each rule configured as `regex` or `regex+ai`, an additional `<id>_source` column is written in the output CSV, recording whether the value was assigned by `"regex"` or `"ai"`. This enables auditing the per-dimension coverage rate of each phase.*

---

### Limitações / Limitations

- **Determinismo parcial:** `temperature=0` reduz mas não elimina variabilidade entre execuções, especialmente em casos ambíguos.
- **Escopo regex restrito:** a fase de regex usa apenas `Title` e `Author Keywords`, sacrificando recall em favor de precisão; artigos ambíguos no título são remetidos à IA.
- **Dependência do modelo externo:** a classificação depende da disponibilidade e comportamento da API Gemini; mudanças na política de saída do modelo entre execuções podem introduzir inconsistências.
- **Sem validação automática:** não há cálculo automático de concordância entre anotadores (e.g., kappa); a validação de qualidade requer amostragem manual.
- **Taxonomia fechada:** as dimensões `target` e `task` usam vocabulários controlados; artigos que não se enquadram são classificados como `"outro"`, o que pode agrupar casos heterogêneos.
