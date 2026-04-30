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
- **Resumable sessions** — classification can be paused and continued without losing progress
- **CSV in, CSV out** — all original columns are preserved in the output

---

## Classified columns

| Column | Type | Description |
|--------|------|-------------|
| `target` | closed list | What the model predicts: wind speed, power, both, or other |
| `architecture` | multiple atomic tags | Architectural components of the proposed model |
| `model` | free text | Exact name or acronym of the proposed model |
| `complementary_technique` | free text | Optimization, training paradigm, or methodological strategy |
| `task` | closed list | Primary research task of the paper |

### Architecture tags

Atomic and combinable — a paper receives all tags that apply to its proposed model:

| Tag | Examples |
|-----|---------|
| Transformer | Informer, PatchTST, Crossformer, iTransformer, Autoformer, TFT |
| State Space Model | Mamba, S4, S5, TimeMachine |
| Rede Recorrente | LSTM, GRU, BiLSTM, RNN, Elman, xLSTM |
| Rede Convolucional | CNN, TCN, ResNet, ConvLSTM, WaveNet |
| Rede de Grafos | GCN, GAT, AGCRN, DCRNN, STGCN |
| MLP-based | N-BEATS, N-HiTS, TSMixer, TiDE |
| Atenção | Self-Attention added to non-Transformer backbones |
| Decomposição | EMD, VMD, CEEMDAN, Wavelet, SSA, STL |
| Ensemble | XGBoost, LightGBM, Random Forest, CatBoost, Stacking |
| Estatístico | ARIMA, SARIMA, ETS, Prophet, Bayesian DLM, Weibull |
| Probabilístico | DeepAR, Gaussian Process, Quantile Regression, CSDI |
| Físico | NWP, WRF, CFD, PINN |
| Neuro-Fuzzy | ANFIS, FIS+NN |
| LLM | GPT, LLaMA adapted for time series |
| Foundation Model | TimeGPT, Chronos, Lag-Llama, Moirai |
| Outro | KAN, Diffusion Models, Quantum NN, RL |

### Task categories

`previsão` · `otimização` · `avaliação de recurso` · `controle` · `modelagem de curva` · `detecção de anomalias` · `geração de dados` · `simulação física` · `avaliação de risco` · `revisão` · `outro`

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
A CSV file with at least `Title` and `Abstract` columns. When available, `Author Keywords` and `Index Keywords` are also used to improve inference. Any additional columns are preserved unchanged in the output.

---

## How it works (technical notes)

**Modular prompt engineering**
Each column has an independent prompt block. BIIA assembles only the blocks for selected columns into a single prompt, reducing token consumption and improving classification focus.

**Fill modes**
- *Fill empty* — skips rows that already have a value; useful for resuming interrupted sessions
- *Overwrite all* — reprocesses every row; useful after refining the taxonomy
- *Overwrite `-` and `outro`* — reprocesses only ambiguous or unclassified rows
- *Overwrite legacy taxonomy* — reprocesses rows classified under a previous taxonomy version

**Atomic architecture tags**
Unlike single-label classification, the `architecture` column supports comma-separated tags. This reflects the reality of hybrid models — a paper proposing VMD+BiLSTM+Attention is tagged as `Decomposição, Rede Recorrente, Atenção` rather than forcing a single imprecise label. Tags were designed with an external domain expert and follow a decision flowchart to ensure consistency.

**Robust JSON parsing**
If the model returns malformed JSON (e.g., due to special characters in abstracts), BIIA attempts object-level recovery before skipping the batch silently.

---

## CSV output example

```
Title,Abstract,Author Keywords,doi,year,target,architecture,model,complementary_technique,task
"Wind speed forecasting...","This paper proposes...","wind speed; LSTM; VMD","10.xxx",2025,"velocidade do vento","Decomposição, Rede Recorrente","VMD+BiLSTM","PSO","previsão"
```

---

## License

MIT — free to use, modify, and distribute with attribution.

---

## Context

Developed as a support tool for a systematic review of machine learning methods applied to wind energy forecasting. The classification taxonomy was iteratively refined through analysis of 2,342 papers, with contributions from a domain expert in time series architectures.
