# BIIA — Bibliographic AI

> A browser-based AI assistant for systematic literature review classification, built as a Progressive Web App (PWA).

BIIA was developed as part of a systematic literature review on **wind energy forecasting**, with a focus on classifying papers by predicted variable, model architecture, complementary techniques, and research task. Although designed for wind energy, the tool is domain-agnostic and can be adapted for any field.

---

## Features

- **No installation required** — runs entirely in the browser as a PWA (installable on desktop and mobile)
- **Selective classification** — choose which columns to classify in each session
- **Fill modes per column** — fill empty cells only, overwrite everything, or reprocess unclear values (`-` and `outro`)
- **Dynamic prompt construction** — the prompt sent to the AI is built automatically based on selected columns, minimizing token usage
- **Multiple architecture tags** — a single paper can be tagged with multiple architectural families (e.g., `Rede Neural, Graph Neural Network`)
- **Live prompt preview** — inspect the exact prompt before running
- **Resumable sessions** — classification can be paused and continued without losing progress
- **CSV in, CSV out** — all original columns are preserved in the output

---

## Classified columns

| Column | Type | Description |
|--------|------|-------------|
| `target` | closed list | What the model predicts: wind speed, power, both, or other |
| `architecture` | multiple tags | Architectural family(ies) of the proposed model |
| `model` | free text | Exact name or acronym of the proposed model |
| `complementary_technique` | free text | Optimization, training paradigm, or methodological strategy |
| `task` | closed list | Primary research task of the paper |

### Architecture families

The taxonomy was developed through iterative analysis of 331 sampled papers:

| Family | Examples |
|--------|---------|
| Transformer | Informer, PatchTST, Mamba, Crossformer, Autoformer |
| Rede Neural | LSTM, GRU, BiLSTM, CNN, TCN, MLP |
| Graph Neural Network | GCN, GAT, AGCRN, DCRNN |
| Ensemble | XGBoost, LightGBM, Random Forest, Stacking |
| Híbrido Deep Learning | CNN+LSTM, BiGRU+TCN |
| Híbrido Atenção | LSTM+Attention, BiGRU+Self-Attention |
| Híbrido Estatístico-ML | Weibull+GBM, ARIMA+LSTM |
| Híbrido Físico-ML | PINN+NN, SDE+NN, WRF+DL |
| Híbrido Decomposição-ML | EMD+LSTM, VMD+GRU, CEEMDAN+Transformer |
| Neuro-Fuzzy | ANFIS, FIS+NN |
| LLM | GPT, LLaMA adapted for time series |
| Estatístico | ARIMA, SARIMA, Bayesian DLM |
| Físico | NWP, WRF, CFD, LES |
| Outro | KAN, Diffusion Models, Quantum NN |

### Task categories

`previsão` · `otimização` · `avaliação de recurso` · `controle` · `modelagem de curva` · `detecção de anomalias` · `geração de dados` · `simulação física` · `avaliação de risco` · `revisão` · `outro`

---

## How to use

### Online (recommended)
Access the hosted version at: `https://<your-username>.github.io/biia`

### Install as PWA
1. Open the URL in Chrome or Samsung Internet
2. Tap the browser menu → **"Add to home screen"** or **"Install app"**
3. BIIA runs as a standalone app, offline-capable

### API key
BIIA uses the [Google Gemini API](https://aistudio.google.com). You will need a free API key:
1. Visit [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** → **Create API key**
3. Paste the key into BIIA on first launch — it is stored only on your device

> The free tier supports up to 15 requests per minute. BIIA automatically throttles requests to stay within limits.

### Input format
A CSV file with at least `title` and `abstract` columns. Any additional columns (e.g., `doi`, `year`, `authors`) are preserved unchanged in the output.

---

## How it works (technical notes)

**Prompt engineering**
Each column has an independent prompt block. When you select columns to classify, BIIA assembles only the relevant blocks into a single prompt. This reduces token consumption and improves classification focus.

**Fill modes**
- *Fill empty* — skips rows that already have a value, useful for resuming interrupted sessions
- *Overwrite all* — reprocesses every row, useful after refining the taxonomy
- *Overwrite `-` and `outro`* — reprocesses only ambiguous or unclassified rows

**Model fallback**
BIIA tries Gemini models in order of preference (`gemini-3-flash-preview` → `gemini-2.5-flash` → `gemini-2.0-flash`), automatically falling back if a model is unavailable for your API key.

**Architecture as multiple tags**
Unlike single-label classification, the `architecture` column supports comma-separated tags. This reflects the reality of hybrid models — a paper proposing CEEMDAN+VMD+Transformer+GRU is tagged as `Híbrido Decomposição-ML, Transformer, Rede Neural` rather than forcing a single imprecise label.

---

## CSV output example

```
title,abstract,doi,year,target,architecture,model,complementary_technique,task
"Wind speed forecasting...","This paper proposes...","10.xxx",2025,"velocidade do vento","Híbrido Decomposição-ML, Rede Neural","CEEMDAN+VMD+GRU","PSO","previsão"
```

---

## License

MIT — free to use, modify, and distribute with attribution.

---

## Context

Developed as a support tool for a systematic review of machine learning methods applied to wind energy forecasting. The classification taxonomy was iteratively refined through analysis of 2,342 papers.
