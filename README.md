# BIIA — bibliografia + ia

> A browser-based AI assistant for systematic literature review classification, built as a Progressive Web App (PWA).

**🔗 [https://tathianamb.github.io/biia/](https://tathianamb.github.io/biia/)**

BIIA was developed as part of a systematic literature review on **wind energy forecasting**, with a focus on classifying papers by predicted variable, model architecture, complementary techniques, and research task. Although designed for wind energy, the tool is domain-agnostic and can be adapted for any field.

---

## Features

- **No installation required** — runs entirely in the browser as a PWA (installable on desktop and mobile)
- **Selective classification** — choose which columns to classify in each session
- **Fill modes per column** — fill empty cells only, overwrite everything, or reprocess unclear values
- **Three-phase classification** — regex pre-classification followed by two parallel API phases
- **Dynamic prompt construction** — the prompt sent to the AI is built automatically based on selected columns
- **Rich context inference** — uses `Title`, `Abstract`, `Author Keywords`, and `Index Keywords`
- **Atomic architecture tags** — a single paper receives all applicable tags
- **Live prompt preview** — inspect the exact prompt before running
- **Real payload preview** — see the exact content sent to the API for the first article
- **Resumable sessions** — classification can be paused and continued without losing progress
- **Automatic retry with backoff** — on API failure, retries automatically with increasing wait times
- **CSV in, CSV out** — all original columns are preserved in the output

---

## Classified columns

| Column | Type | Description |
|--------|------|-------------|
| `target` | closed list | What the model predicts: wind speed, power, or other |
| `architecture` | multiple atomic tags | Architectural components of the proposed model |
| `model` | free text | Exact name or acronym of the proposed model |
| `complementary_technique` | free text | Optimization, training paradigm, or methodological strategy |
| `task` | closed list | Primary research task of the paper |

### Target values

Classification follows a strict hierarchy applied in order:

| Priority | Value | Rule |
|----------|-------|------|
| 1 | `velocidade do vento` | Paper proposes a model whose primary output is wind speed |
| 2 | `potência` | Model forecasts power output from any source (wind, solar, etc.) and does not fall under rule 1 |
| 3 | `outro` | Does not forecast wind speed or power, is not a forecasting paper, or not applicable |

### Task values

| Value | Description |
|-------|-------------|
| `previsão` | Forecasting of wind speed, wind power, or meteorological variables |
| `otimização` | Scheduling, dispatch, storage, market bidding, grid management |
| `avaliação de recurso` | Wind potential assessment, Weibull fitting, site analysis |
| `controle` | Wake control, pitch control, frequency control |
| `modelagem de curva` | Power curve modeling |
| `detecção de anomalias` | Anomaly detection, fault detection, fault diagnosis |
| `geração de dados` | Data augmentation, synthetic data generation |
| `simulação física` | CFD, WRF, LES as the primary model |
| `avaliação de risco` | Risk assessment, uncertainty quantification as primary focus |
| `revisão` | Systematic review, survey, benchmark, comparative study |
| `outro` | Does not fit the above categories |

---

## Classification methodology

### Three-phase pipeline

BIIA classifies papers through three sequential phases. Phases 2 and 3 run in parallel to minimize total processing time.

```
Phase 1 — Regex (instantaneous, no API calls)
  └─ Classifies task and target for all papers
  └─ Papers without a confident match receive 'outro'

Phase 2 — API: task and target        ─┐
  └─ Only papers where regex → 'outro'  ├─ run in parallel
                                         │
Phase 3 — API: architecture, model,   ─┘
          complementary_technique
  └─ All papers requiring these columns
```

This design significantly reduces API usage: only ambiguous cases reach the API for `task` and `target`, while `architecture`, `model`, and `complementary_technique` always require AI inference.

---

### Phase 1 — Regex classification

Regex classification is conservative by design: it only assigns a value when there is high confidence in the match. When in doubt, the paper falls through to `outro` and is handled by the API in Phase 2.

#### Search scope

| Column | Search fields |
|--------|--------------|
| `task` | Title + Author Keywords + Index Keywords (except `previsão`: Title only) |
| `target` | Title + Author Keywords + Index Keywords |

The abstract is intentionally excluded from regex search. Terms such as "forecasting", "optimization", or "wind speed" frequently appear in the abstract as context, background, or baseline description — not as the paper's primary contribution. Restricting search to the title and keywords yields higher precision at the cost of recall, with the API handling the remaining cases.

#### Task hierarchy

Rules are tested in order. The first match wins.

| Priority | Task | Trigger terms |
|----------|------|---------------|
| 1 | `revisão` | "systematic review", "literature survey" |
| 2 | `simulação física` | "CFD", "LES", "WRF" |
| 3 | `detecção de anomalias` | "anomaly detection", "fault detection", "fault diagnosis" |
| 4 | `geração de dados` | "data augmentation", "synthetic data" |
| 5 | `avaliação de risco` | "risk assessment" |
| 6 | `controle` | "wake control", "pitch control", "frequency control" |
| 7 | `modelagem de curva` | "power curve" |
| 8 | `avaliação de recurso` | "resource assessment", "wind potential" |
| 9 | `otimização` | "scheduling", "dispatch", "arbitrage", "unit commitment" |
| 10 | `previsão` | "forecasting", "prediction" — **Title only** |
| 11 | `outro` | No match → sent to API |

**Key design decisions:**

- `otimização` is tested **before** `previsão` because optimization papers frequently mention forecasting as a subcomponent (e.g., "optimization of wind power forecasting"). The reverse is not true.
- `previsão` is restricted to the title only, as "forecasting" and "prediction" appear in virtually every wind energy abstract regardless of the paper's primary task.
- Terms are kept to a maximum of two words to maximize match rate while preserving specificity. Longer phrases are too rare to be useful.
- `optimization` alone is deliberately excluded from the `otimização` trigger terms, as it commonly refers to model hyperparameter optimization rather than operational optimization.
- `SCADA` alone is excluded from `detecção de anomalias` because SCADA data is used across multiple tasks including forecasting.

#### Target hierarchy

| Priority | Target | Trigger terms |
|----------|--------|---------------|
| 1 | `velocidade do vento` | "wind speed" |
| 2 | `potência` | "wind power" |
| 3 | `outro` | No match → sent to API |

**Key design decisions:**

- Only `wind power` is used for `potência` — broader terms like "power output" or "power generation" risk false positives in papers that discuss power as context rather than as the forecasting target.
- `target` classification is independent of `task` — the regex acts directly on the text without requiring a prior task classification.

---

### Phase 2 — API for task and target

Papers where the regex returned `outro` for `task` or `target` are sent to the Gemini API in batches of 5, with a 6-second interval between batches. The prompt contains only the blocks for the columns being classified, minimizing token usage.

The API prompt for `task` and `target` follows the same hierarchy as the regex rules, but expressed in natural language with additional context and examples that the model can leverage for ambiguous cases.

---

### Phase 3 — API for architecture, model, and complementary_technique

All papers requiring classification of `architecture`, `model`, or `complementary_technique` are processed via the Gemini API in parallel with Phase 2. These columns cannot be reliably classified by regex because they require understanding the proposed model's structure from the abstract.

#### Modular prompt engineering

Each column has an independent prompt block. BIIA assembles only the blocks for the selected columns, reducing token consumption and allowing each block to be refined independently.

#### Automatic retry with backoff

Both Phase 2 and Phase 3 implement automatic retry with exponential backoff:
- Attempts 1–3: wait 2 minutes before retrying
- Attempt 4 onward: wait 5 minutes before retrying
- Classification never stops automatically — only the user can pause it

A countdown timer is displayed during wait periods. The attempt counter resets after each successful batch.

---

### Architecture taxonomy

The taxonomy uses atomic, combinable tags. Any model, however complex, is described as a combination of these atoms. A paper receives all tags that apply to its proposed model.

| Tag | Description | Examples |
|-----|-------------|---------|
| **Transformer** | Self-attention as the central mechanism | Informer, PatchTST, Crossformer, iTransformer, Autoformer, TFT |
| **State Space Model** | Neural state-space models — non-attentional sequential processing | Mamba, S4, S5, TimeMachine |
| **Rede Recorrente** | Explicit temporal recurrence with gating | LSTM, GRU, BiLSTM, RNN, Elman, xLSTM |
| **Rede Convolucional** | Local feature extraction via convolutions | CNN, TCN, ResNet, ConvLSTM, WaveNet |
| **Rede de Grafos** | Models over graph structures | GCN, GAT, AGCRN, DCRNN, STGCN |
| **MLP-based** | Multi-layer perceptrons with specialized blocks | N-BEATS, N-HiTS, TSMixer, TiDE |
| **Atenção** | Attention added to a non-Transformer backbone | LSTM+Attention, CNN+Multi-head Attention |
| **Decomposição** | Signal decomposition as preprocessing | EMD, VMD, CEEMDAN, Wavelet, SSA, STL |
| **Ensemble** | Combination of multiple models or trees | XGBoost, LightGBM, Random Forest, CatBoost, Stacking |
| **Estatístico** | Classical statistical models | ARIMA, SARIMA, ETS, Prophet, Bayesian DLM, Weibull |
| **Probabilístico** | Models producing distributions or intervals | DeepAR, Gaussian Process, Quantile Regression, CSDI |
| **Físico** | Physics-based or simulation models | NWP, WRF, CFD, PINN |
| **Neuro-Fuzzy** | Fuzzy inference combined with neural networks | ANFIS, FIS+NN |
| **LLM** | General-purpose large language models adapted for time series | GPT, LLaMA |
| **Foundation Model** | Models pre-trained specifically for time series | TimeGPT, Chronos, Lag-Llama, Moirai |
| **Outro** | Not classifiable in the above | KAN, Diffusion Models, Quantum NN, RL |

#### Decision flowchart

The AI follows this flowchart when classifying `architecture`:

1. Is there signal decomposition? → add `Decomposição`
2. Does it incorporate physics or simulation? → add `Físico`
3. Identify the predictive backbone(s) → add all applicable tags
4. Is there an attention mechanism on a non-Transformer backbone? → add `Atenção`
5. Does the model produce distributions or prediction intervals? → add `Probabilístico`

#### Design rationale

**Why atomic tags instead of hybrid families?**
An earlier version used composite families such as `Híbrido Decomposição-ML`. This became unsustainable as the dataset revealed increasingly complex architectures. Atomic tags allow any combination to be expressed without modifying the taxonomy. The trade-off is that a single paper contributes to multiple tag counts simultaneously, which must be accounted for in quantitative analyses.

**Why is `Atenção` separate from `Transformer`?**
The Transformer uses self-attention as its core structural element — adding `Atenção` to a Transformer would be redundant. The `Atenção` tag is reserved for attention grafted onto a non-Transformer backbone as an enhancement.

**Why is `Probabilístico` orthogonal?**
A model can be probabilistic regardless of its backbone. DeepAR uses recurrent layers but produces distributions; TFT is Transformer-based but also probabilistic. Treating `Probabilístico` as orthogonal allows this dimension to be analyzed independently.

**Why are `LLM` and `Foundation Model` separate?**
LLMs (GPT, LLaMA) are general-purpose models adapted for time series through prompting or fine-tuning. Foundation models for time series (TimeGPT, Chronos) are pre-trained specifically on time series data. The distinction matters for understanding the role of pre-training in wind energy forecasting research.

---

## Fill modes

Each selected column can be configured independently:

| Mode | Behavior |
|------|----------|
| Preencher vazios | Skips rows that already have a value — useful for resuming sessions |
| Sobrescrever tudo | Reprocesses every row — useful after refining the taxonomy |
| Sobrescrever outro | Reprocesses only rows classified as `outro` — useful for reviewing ambiguous cases |

---

## How to use

### Online (recommended)
**[https://tathianamb.github.io/biia/](https://tathianamb.github.io/biia/)**

### Install as PWA
1. Open the URL in Chrome or Samsung Internet
2. Tap the browser menu → **"Add to home screen"** or **"Install app"**
3. BIIA runs as a standalone app

### API key
BIIA uses the [Google Gemini API](https://aistudio.google.com). You will need a free API key:
1. Visit [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** → **Create API key**
3. Paste the key into BIIA on first launch — it is stored only on your device

> The free tier supports up to 15 requests per minute. BIIA paces requests to stay within limits, and retries automatically on failure.

### Input format
A CSV file with at least `Title` and `Abstract` columns. When available, `Author Keywords` and `Index Keywords` are also used. Column names are case-insensitive. Any additional columns are preserved unchanged in the output.

---

## CSV output example

```
Title,Abstract,Author Keywords,doi,year,target,architecture,model,complementary_technique,task
"Wind speed forecasting...","This paper proposes...","wind speed; LSTM; VMD","10.xxx",2025,"velocidade do vento","Decomposição, Rede Recorrente","VMD+BiLSTM","PSO","previsão"
```

---

## License

MIT — free to use, modify, and distribute with attribution.
