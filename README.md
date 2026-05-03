# BIIA — bibliografia + ia

> A browser-based AI assistant for systematic literature review classification, built as a Progressive Web App (PWA).

**🔗 [https://tathianamb.github.io/biia/](https://tathianamb.github.io/biia/)**

BIIA was developed as part of a systematic literature review on **wind energy forecasting**, with a focus on classifying papers by predicted variable, model architecture, complementary techniques, and research task. Although designed for wind energy, the tool is domain-agnostic and can be adapted for any field.

---

## Features

- **No installation required** — runs entirely in the browser as a PWA (installable on desktop and mobile)
- **Selective classification** — choose which columns to classify in each session
- **Fill modes per column** — fill empty cells only, overwrite everything, reprocess unclear values, or reprocess legacy taxonomy values
- **Dynamic prompt construction** — the prompt sent to the AI is built automatically based on selected columns, minimizing token usage
- **Rich context inference** — uses `Title`, `Abstract`, `Author Keywords`, and `Index Keywords` to improve classification accuracy
- **Atomic architecture tags** — a single paper receives all applicable tags (e.g., `Decomposição, Rede Recorrente, Atenção`)
- **Live prompt preview** — inspect the exact prompt before running
- **Real payload preview** — see the exact content sent to the API for the first article in your CSV
- **Resumable sessions** — classification can be paused and continued without losing progress
- **Automatic retry** — on API failure, retries automatically (2 min interval for first 3 attempts, 5 min thereafter)
- **CSV in, CSV out** — all original columns are preserved in the output

---

## Classified columns

| Column | Type | Description |
|--------|------|-------------|
| `target` | closed list | What the model predicts: wind speed, power (any source), both, or other |
| `architecture` | multiple atomic tags | Architectural components of the proposed model |
| `model` | free text | Exact name or acronym of the proposed model |
| `complementary_technique` | free text | Optimization, training paradigm, or methodological strategy |
| `task` | closed list | Primary research task of the paper |

### Target values

| Value | Description |
|-------|-------------|
| `velocidade do vento` | Forecasting of wind speed |
| `potência` | Forecasting of power output from any source (wind, solar, etc.) |
| `ambos` | Simultaneously forecasts wind speed and another target variable |
| `outro` | Any other variable, non-forecasting paper, or not applicable (reviews, optimization, etc.) |

---

## Classification methodology

### Modular prompt engineering

Each column has an independent prompt block containing its classification instructions, valid values, rules, and examples. When a classification session starts, BIIA assembles only the blocks corresponding to the selected columns into a single prompt. This design has two practical advantages: it reduces token consumption by avoiding unnecessary instructions, and it allows each column to be refined independently without affecting the others.

The prompt is sent to the Gemini API along with the title, abstract, author keywords, and index keywords of each article in the batch. The model is instructed to respond only with a JSON array — no markdown, no explanations — which is then parsed and written back to the corresponding columns in memory.

### Decision flowchart for architecture

The classification of the `architecture` column follows a structured decision flowchart developed with an external domain expert in time series architectures:

1. **Is there signal decomposition?** → add `Decomposição`
2. **Does it incorporate physics or simulation?** → add `Físico`
3. **Identify the predictive backbone(s)** → add all applicable architecture tags
4. **Is there an attention mechanism coupled to a non-Transformer backbone?** → add `Atenção`
5. **Does the model produce distributions or prediction intervals?** → add `Probabilístico`

This flowchart ensures that hybrid models are described completely rather than collapsed into a single imprecise label. A model combining VMD decomposition, a BiLSTM backbone, and an attention mechanism is tagged as `Decomposição, Rede Recorrente, Atenção` — each dimension independently queryable in the analysis.

---

## Architecture taxonomy

The taxonomy uses atomic, combinable tags. Rather than defining families for every possible hybrid combination, each tag represents a single architectural concept. Any model, however complex, is described as a combination of these atoms.

| Tag | Description | Examples |
|-----|-------------|---------|
| **Transformer** | Self-attention as the central mechanism | Informer, PatchTST, Crossformer, iTransformer, Autoformer, TFT |
| **State Space Model** | Neural state-space models — non-attentional, non-recurrent sequential processing | Mamba, S4, S5, TimeMachine |
| **Rede Recorrente** | Explicit temporal recurrence with gating mechanisms | LSTM, GRU, BiLSTM, RNN, Elman, xLSTM |
| **Rede Convolucional** | Local feature extraction via convolutions | CNN, TCN, ResNet, ConvLSTM, WaveNet |
| **Rede de Grafos** | Models defined over graph structures for spatial-temporal dependencies | GCN, GAT, AGCRN, DCRNN, STGCN |
| **MLP-based** | Multi-layer perceptrons with residual or specialized blocks | N-BEATS, N-HiTS, TSMixer, TiDE |
| **Atenção** | Attention mechanism added to a non-Transformer backbone | LSTM+Attention, CNN+Multi-head Attention |
| **Decomposição** | Signal decomposition as a preprocessing component | EMD, VMD, CEEMDAN, ICEEMDAN, Wavelet, SSA, STL |
| **Ensemble** | Combination of multiple models or trees | XGBoost, LightGBM, Random Forest, CatBoost, Stacking |
| **Estatístico** | Classical statistical models | ARIMA, SARIMA, ETS, Prophet, VAR, Bayesian DLM, Weibull |
| **Probabilístico** | Models that produce distributions or prediction intervals | DeepAR, Gaussian Process, Quantile Regression, CSDI |
| **Físico** | Physics-based or simulation models | NWP, WRF, CFD, PINN |
| **Neuro-Fuzzy** | Fuzzy inference systems combined with neural networks | ANFIS, FIS+NN |
| **LLM** | General-purpose large language models adapted for time series | GPT, LLaMA |
| **Foundation Model** | Models pre-trained specifically for time series forecasting | TimeGPT, Chronos, Lag-Llama, Moirai |
| **Outro** | Architectures not classifiable in the above | KAN, Diffusion Models, Quantum NN, RL |

### Design rationale

**Why atomic tags instead of hybrid families?**
An earlier version of this taxonomy used composite families such as `Híbrido Decomposição-ML` or `Híbrido Deep Learning`. This approach required a fixed set of combinations to be defined upfront, which became unsustainable as the dataset revealed increasingly complex architectures. Atomic tags solve this by allowing any combination to be expressed without modifying the taxonomy. The trade-off is that a single paper can contribute to multiple tag counts simultaneously, which must be accounted for in quantitative analyses.

**Why is `Atenção` separate from `Transformer`?**
The Transformer architecture uses self-attention as its core structural element. Adding `Atenção` to a Transformer would be redundant. The `Atenção` tag is reserved for cases where an attention mechanism is grafted onto a non-Transformer backbone — typically LSTM, GRU, or CNN — as an enhancement rather than as a defining structural choice.

**Why is `Probabilístico` orthogonal?**
A model can be probabilistic regardless of its backbone. DeepAR uses recurrent layers but produces distributions; TFT is Transformer-based but also probabilistic. Treating `Probabilístico` as orthogonal to architectural families allows this dimension to be analyzed independently without creating a separate family for every probabilistic variant of every architecture.

**Why are `LLM` and `Foundation Model` separate?**
Large language models (GPT, LLaMA) are general-purpose models adapted for time series through prompting or fine-tuning — the time series domain is not their primary training objective. Foundation models for time series (TimeGPT, Chronos) are pre-trained specifically on time series data and are used as zero-shot or few-shot predictors. The distinction matters for understanding the role of pre-training in wind energy forecasting research.

---

## Task categories

| Value | Description |
|-------|-------------|
| `previsão` | Forecasting of wind speed, wind power, or meteorological variables |
| `otimização` | Scheduling, dispatch, storage, market bidding, grid management |
| `avaliação de recurso` | Wind potential assessment, Weibull fitting, site analysis |
| `controle` | Wake control, pitch control, frequency control |
| `modelagem de curva` | Power curve modeling |
| `detecção de anomalias` | Outlier detection, fault detection, SCADA data cleaning |
| `geração de dados` | Data augmentation, synthetic data generation |
| `simulação física` | CFD, WRF, LES as the primary model |
| `avaliação de risco` | Risk assessment, uncertainty quantification as primary focus |
| `revisão` | Systematic review, survey, benchmark, comparative study |
| `outro` | Does not fit the above categories |

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

> The free tier supports up to 15 requests per minute. BIIA automatically paces requests to stay within limits.

### Input format
A CSV file with at least `Title` and `Abstract` columns. When available, `Author Keywords` and `Index Keywords` are also used to improve inference. Column names are case-insensitive. Any additional columns are preserved unchanged in the output.

### Fill modes
Each selected column can be configured independently:

| Mode | Behavior |
|------|----------|
| Preencher vazios | Skips rows that already have a value — useful for resuming interrupted sessions |
| Sobrescrever tudo | Reprocesses every row — useful after refining the taxonomy or the prompt |
| Sobrescrever outro | Reprocesses only rows classified as `outro` — useful for reviewing ambiguous cases |

---

## CSV output example

```
Title,Abstract,Author Keywords,doi,year,target,architecture,model,complementary_technique,task
"Wind speed forecasting...","This paper proposes...","wind speed; LSTM; VMD","10.xxx",2025,"velocidade do vento","Decomposição, Rede Recorrente","VMD+BiLSTM","PSO","previsão"
```

---

## License

MIT — free to use, modify, and distribute with attribution.
