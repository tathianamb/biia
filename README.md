# BIIA — Bibliography + AI

A browser-based tool for AI-assisted classification in systematic literature reviews.

**Live application:** [https://tathianamb.github.io/biia/](https://tathianamb.github.io/biia/)

---

## Overview

BIIA (*bibliografia + ia*) is an open-source, client-side web application designed to support the screening and coding phase of systematic literature reviews (SLRs). It accepts a CSV export from bibliographic databases, applies user-defined classification rules using a combination of regular expressions and a large language model (LLM), and produces an enriched CSV with one column per coded dimension.

The tool was originally developed for a systematic literature review on **wind energy forecasting**, with a coding scheme covering the predicted variable, model architecture, proposed model name, complementary techniques, and primary research task. It is domain-agnostic: the classification rules, LLM prompts, and output columns are fully configurable by the user.

BIIA runs entirely in the browser. It requires no installation, no server, and no local model — users provide a Google Gemini API key, which is stored only on the local device.

---

## Methodology

### Two-phase classification pipeline

BIIA classifies papers in two sequential phases. The phases are architecturally separated: regex runs first and completely; the AI phase then processes only the records left unclassified.

```
Phase 1 — Regex  (synchronous, no API calls)
  └─ Applied to every rule configured as "regex" or "regex+ai"
  └─ The first matching pattern wins; unmatched records are left empty

Phase 2 — AI  (parallel, independent streams)
  └─ One async stream per rule configured as "ai" or "regex+ai"
  └─ All streams run concurrently (Promise.all)
  └─ Each stream processes only records left empty after Phase 1
```

This design reflects a deliberate precision-recall trade-off: regex rules use a restricted scope (title and author keywords only, never the abstract) and conservative trigger terms, maximising specificity at the cost of recall. The AI phase recovers unmatched records. Together, the two phases provide full coverage.

### AI inference parameters

All API calls used the following parameters:

| Parameter | Value |
|-----------|-------|
| Provider | Google Gemini API (v1beta) |
| Models (fallback order) | `gemini-3.1-flash-lite` → `gemma-4-31b-it` → `gemma-4-26b-a4b-it` |
| `temperature` | `0` |
| `maxOutputTokens` | `2048` |
| Batch size | 5 records per request |
| Inter-batch pause | 6 seconds |
| Retry wait — attempts 1–3 | 2 minutes |
| Retry wait — attempt 4+ | 5 minutes |
| Response format | JSON array: `[{"index": N, "<field>": "value"}]` |

`temperature = 0` was chosen to maximise determinism. The batch size of 5 and the 6-second inter-batch pause keep request throughput within the free-tier rate limit of 15 requests per minute.

### Prompt design

Each classification dimension has its own independent prompt, containing only the fields configured for that rule. This minimises token usage and allows prompts to be refined independently. The model is instructed to return a JSON array only, without markdown wrappers; a regex-based fallback parser recovers partial responses when the primary JSON parse fails.

The following sections document the exact prompts used in the wind energy review.

---

## Default coding scheme (wind energy forecasting)

The five dimensions below are the built-in presets. They were designed for a systematic review on wind energy forecasting and can be used as-is, modified, or replaced.

### Dimension 1 — `target`: Predicted variable

| Method | Input fields |
|--------|-------------|
| `regex+ai` | Title, Author Keywords |

#### Values

| Value | Definition |
|-------|-----------|
| `velocidade do vento` | The proposed model's primary output is wind speed |
| `potência` | The model forecasts power output (any source) and does not meet the wind speed criterion |
| `outro` | Any other output variable, no clear proposed model, or not applicable |

#### Regex rules (evaluated in order; first match wins)

| Pattern | Assigned value |
|---------|---------------|
| `/wind speed/i` | `velocidade do vento` |
| `/wind power/i` | `potência` |
| *(no match)* | empty → Phase 2 |

**Design rationale.** Only `wind power` triggers `potência`; broader terms such as `power output` or `power generation` generate false positives in papers that discuss power as background context rather than as the forecasting target.

#### Prompt (exact string sent to the API)

```
Você é um especialista em ML.
Analise o título e palavras-chave de cada artigo e classifique o campo abaixo:

━━ target ━━
Variável alvo do modelo proposto. Siga a HIERARQUIA abaixo em ordem:
1. "velocidade do vento": o modelo tem velocidade do vento como variável de saída
2. "potência": o modelo tem potência como variável de saída (qualquer fonte: eólica, solar, etc.) e NÃO se enquadra na regra anterior
3. "outro": outra variável de saída, sem modelo proposto claro, ou não aplicável
```

---

### Dimension 2 — `task`: Primary research task

| Method | Input fields |
|--------|-------------|
| `regex+ai` | Title, Author Keywords |

#### Values

| Value | Definition |
|-------|-----------|
| `previsão` | Forecasting of wind speed, power, or meteorological variables |
| `otimização` | Scheduling, dispatch, storage, market bidding, grid management |
| `avaliação de recurso` | Wind potential assessment, Weibull fitting, site analysis |
| `controle` | Wake control, pitch control, frequency control |
| `modelagem de curva` | Power curve modelling |
| `detecção de anomalias` | Anomaly detection, fault detection, SCADA data cleaning |
| `geração de dados` | Data augmentation, synthetic data generation |
| `simulação física` | CFD, WRF, or LES as the primary model |
| `avaliação de risco` | Risk assessment or uncertainty quantification as the primary focus |
| `revisão` | Systematic review, survey, benchmark, or comparative study |
| `outro` | Does not fit the above categories |

#### Regex rules (evaluated in order; first match wins)

| Priority | Patterns | Assigned value |
|----------|---------|---------------|
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
| — | *(no match)* | empty → Phase 2 |

**Design rationale.**
- `otimização` is tested before `previsão` because optimisation papers frequently mention forecasting as a subcomponent (e.g., *optimisation of wind power forecasting*); the reverse is not true.
- `optimization` alone is excluded from the `otimização` triggers because it commonly refers to hyperparameter optimisation, not operational optimisation.
- `SCADA` alone is excluded from `detecção de anomalias` because SCADA data is used across multiple tasks, including forecasting.
- Trigger terms are kept to at most two words to maximise match rate while preserving specificity; longer phrases are too infrequent to be useful.
- The regex scope is restricted to title and author keywords, not the abstract or index keywords. These terms appear frequently in abstracts as background or baseline description rather than as the paper's primary contribution, reducing precision when the abstract is included.

#### Prompt (exact string sent to the API)

```
Você é um especialista em ML.
Analise o título e palavras-chave de cada artigo e classifique o campo abaixo:

━━ task ━━
Tarefa principal do artigo. Use EXATAMENTE uma das opções:
- "previsão": forecasting de velocidade, potência ou variáveis meteorológicas
- "otimização": scheduling, dispatch, armazenamento, leilão, gestão, feature selection como foco
- "avaliação de recurso": potencial eólico, Weibull, análise de sítio
- "controle": wake control, pitch control, controle de frequência
- "modelagem de curva": power curve modeling
- "detecção de anomalias": outlier detection, fault detection, limpeza SCADA
- "geração de dados": data augmentation, synthetic data
- "simulação física": CFD, WRF, LES como modelo principal
- "avaliação de risco": risk assessment, uncertainty quantification como foco
- "revisão": systematic review, survey, benchmark, comparative study
- "outro": não se encaixa nas anteriores
```

---

### Dimension 3 — `architecture`: Architectural family

| Method | Input fields |
|--------|-------------|
| `ai` | Title, Abstract, Author Keywords, Index Keywords |

Values are **multi-label and combinable**: a paper may receive several tags separated by commas (e.g., `"Transformer, Rede Recorrente"`). Metaheuristics and training paradigms (PSO, transfer learning, federated learning) are not architecture tags — they are classified under `complementary_technique`.

| Tag | Description | Examples |
|-----|-------------|---------|
| `Transformer` | Attention-based backbone as the central mechanism | Informer, PatchTST, Crossformer, Autoformer, Mamba |
| `Rede Recorrente` | Explicit temporal recurrence with gating | LSTM, GRU, BiLSTM, RNN, Elman, xLSTM |
| `Rede Convolucional` | Local feature extraction via convolutions | CNN, TCN, ResNet, ConvLSTM, WaveNet |
| `Rede de Grafos` | Models over graph structures | GCN, GAT, AGCRN, DCRNN, STGCN |
| `MLP-based` | Multi-layer perceptrons with specialised blocks | N-BEATS, N-HiTS, TSMixer, TiDE |
| `Ensemble` | Combinations of multiple models or decision trees | XGBoost, LightGBM, Random Forest, CatBoost, Stacking |
| `Neuro-Fuzzy` | Fuzzy inference combined with neural networks | ANFIS, FIS+NN |
| `LLM` | Large language models adapted for time series | GPT, LLaMA |
| `Estatístico` | Classical statistical models | ARIMA, SARIMA, regression, Bayesian DLM |
| `Físico` | Physics-based or numerical simulation models | NWP, WRF, CFD, LES |
| `Outro` | Not classifiable above | KAN, Diffusion Models, RL, GAM, Quantum NN |
| `-` | No clear proposed model | — |

#### Prompt (exact string sent to the API)

```
Você é um especialista em ML.
Analise o título, palavras-chave e abstract de cada artigo e classifique o campo abaixo:

━━ architecture ━━
Liste as famílias arquiteturais do modelo PROPOSTO. Podem ser MÚLTIPLAS tags separadas por vírgula.
Use APENAS as opções abaixo — inclua todas que compõem a arquitetura proposta:
- "Transformer": backbone baseado em atenção (Transformer, Informer, PatchTST, Mamba, Crossformer, Autoformer)
- "Rede Recorrente": LSTM, GRU, BiLSTM, RNN, Elman, xLSTM
- "Rede Convolucional": CNN, TCN, ResNet, ConvLSTM, WaveNet
- "Rede de Grafos": GCN, GAT, AGCRN, DCRNN, STGCN
- "MLP-based": N-BEATS, N-HiTS, TSMixer, TiDE
- "Ensemble": XGBoost, Random Forest, LightGBM, CatBoost, Stacking
- "Neuro-Fuzzy": sistemas fuzzy + redes neurais (ANFIS, FIS+NN)
- "LLM": Large Language Models para séries temporais (GPT, LLaMA)
- "Estatístico": puramente estatístico (ARIMA, SARIMA, regressão, Bayesian DLM)
- "Físico": puramente físico (NWP, WRF, CFD, LES)
- "Outro": não classificável (KAN, Diffusion, RL puro, GAM, Quantum NN)
- "-": sem modelo proposto claro
REGRAS: Metaheurística e transfer learning NÃO são arquitetura — vão em complementary_technique.
```

---

### Dimension 4 — `model`: Proposed model name

| Method | Input fields |
|--------|-------------|
| `ai` | Title, Abstract, Author Keywords, Index Keywords |

The exact name or acronym of the proposed model (e.g., `"DBANN"`, `"CEEMDAN+VMD+GRU"`, `"PINN+Informer"`). Returns `"-"` when no clear proposed model is identified.

#### Prompt (exact string sent to the API)

```
Você é um especialista em ML.
Analise o título, palavras-chave e abstract de cada artigo e classifique o campo abaixo:

━━ model ━━
Nome/sigla EXATA do modelo proposto (ex: "DBANN", "CEEMDAN+VMD+GRU", "PINN+Informer").
Use "-" se não há modelo proposto claro.
```

---

### Dimension 5 — `complementary_technique`: Complementary techniques

| Method | Input fields |
|--------|-------------|
| `ai` | Title, Abstract, Author Keywords, Index Keywords |

Techniques complementary to the primary architecture: optimisation algorithms, training paradigms, and methodological strategies. Examples: `"PSO"`, `"NSGA-III feature selection"`, `"transfer learning"`, `"federated learning"`, `"meta-learning"`, `"knowledge distillation"`, `"quantile regression"`, `"Monte Carlo"`. Multiple values are separated by commas; `"-"` when none apply.

#### Prompt (exact string sent to the API)

```
Você é um especialista em ML.
Analise o título, palavras-chave e abstract de cada artigo e classifique o campo abaixo:

━━ complementary_technique ━━
Técnicas COMPLEMENTARES à arquitetura: otimização, paradigma de treinamento, estratégia metodológica.
Exemplos: "PSO", "NSGA-III feature selection", "transfer learning", "federated learning",
"meta-learning", "knowledge distillation", "quantile regression", "Monte Carlo".
Use "-" se não há técnica complementar relevante. Múltiplas separadas por vírgula.
```

---

## Source provenance

For each dimension configured as `regex` or `regex+ai`, BIIA writes an additional `<id>_source` column recording whether the value was assigned by `"regex"` or `"ai"`. This enables per-dimension audit of the relative coverage of each phase, and supports quality assessment of the hybrid pipeline.

### Output format

All original CSV columns are preserved. BIIA appends one column per active rule, named by the rule's ID, followed by the corresponding `_source` column where applicable.

**Example output columns for the default presets:**

```
Title, Abstract, Author Keywords, Index Keywords, doi, year,
architecture, model, complementary_technique,
task, task_source,
target, target_source
```

**Example row:**

```csv
"Wind speed forecasting...","This paper proposes...","wind speed; LSTM; VMD","10.xxx",2025,
"Rede Recorrente, Rede Convolucional","VMD+BiLSTM","PSO",
"previsão","regex","velocidade do vento","regex"
```

---

## Reproducibility

### Input format

A CSV file with at least a `Title` column. When available, `Abstract`, `Author Keywords`, and `Index Keywords` are used by the AI rules. Column names are matched as provided (case-sensitive). Any additional columns are preserved unchanged in the output.

### Running the tool

**Online (recommended):** [https://tathianamb.github.io/biia/](https://tathianamb.github.io/biia/)

**Local static server:**
```bash
npx serve .
# or
python -m http.server
```

**API key:** a free Google Gemini API key is required (obtainable at [aistudio.google.com](https://aistudio.google.com)). The key is stored only in the browser's localStorage and never transmitted beyond the Gemini API.

**Rule persistence:** active rules and the user rule library are stored in localStorage and restored on reload, allowing classification sessions to be resumed without data loss.

### Fill modes

Each rule can independently be set to one of two fill modes:

| Mode | Behaviour |
|------|-----------|
| Fill empty only | Skips records that already have a value — enables resuming interrupted sessions |
| Overwrite all | Reprocesses every record — use after revising the taxonomy or prompt |

---

## Limitations

- **Partial determinism.** `temperature = 0` reduces but does not eliminate output variability across runs, particularly for ambiguous records.
- **Restricted regex scope.** The regex phase covers only titles and author keywords, sacrificing recall for precision; ambiguous titles are deferred to the AI phase.
- **Dependence on an external model.** Classification accuracy is contingent on the behaviour of the Gemini API; changes in model policy or output format between runs may introduce inconsistencies.
- **No automated inter-rater reliability.** The tool does not compute agreement statistics (e.g., Cohen's κ); quality validation requires manual sampling.
- **Closed taxonomy for `target` and `task`.** Papers that do not fit the defined values are assigned `"outro"`, which may aggregate heterogeneous cases.

---

## License

MIT — free to use, modify, and distribute with attribution.

---

## Citation

If you use BIIA in a published systematic review, please cite the software repository:

```
Barchi, T. BIIA: Bibliography + AI — a browser-based tool for AI-assisted
systematic literature review classification. GitHub, 2025.
Available at: https://github.com/tathianamb/biia
```
