BIIA -- Bibliography + AI

A browser-based tool for AI-assisted classification in systematic literature reviews.

Live application: https://tathianamb.github.io/biia/

================================================================================

OVERVIEW

BIIA (bibliografia + ia) is an open-source, client-side web application designed
to support the screening and coding phase of systematic literature reviews (SLRs).
It accepts a CSV export from bibliographic databases, applies user-defined
classification rules using a combination of regular expressions and a large
language model (LLM), and produces an enriched CSV with one column per coded
dimension.

The tool was originally developed for a systematic literature review on wind
energy forecasting, with a coding scheme covering the predicted variable, model
architecture, proposed model name, complementary techniques, and primary research
task. It is domain-agnostic: the classification rules, LLM prompts, and output
columns are fully configurable by the user.

BIIA runs entirely in the browser. It requires no installation, no server, and no
local model -- users provide a Google Gemini API key, which is stored only on the
local device.

================================================================================

METHODOLOGY

Two-phase classification pipeline
----------------------------------

BIIA classifies papers in two sequential phases. The phases are architecturally
separated: regex runs first and completely; the AI phase then processes only the
records left unclassified.

  Phase 1 -- Regex  (synchronous, no API calls)
    * Applied to every rule configured as "regex" or "regex+ai"
    * The first matching pattern wins; unmatched records are left empty

  Phase 2 -- AI  (parallel, independent streams)
    * One async stream per rule configured as "ai" or "regex+ai"
    * All streams run concurrently (Promise.all)
    * Each stream processes only records left empty after Phase 1

This design reflects a deliberate precision-recall trade-off: regex rules use a
restricted scope (title and author keywords only, never the abstract) and
conservative trigger terms, maximising specificity at the cost of recall. The AI
phase recovers unmatched records. Together, the two phases provide full coverage.


AI inference parameters
------------------------

All API calls used the following parameters:

  Parameter                    Value
  ---------                    -----
  Provider                     Google Gemini API (v1beta)
  Models (fallback order)      gemini-3.1-flash-lite -> gemma-4-31b-it -> gemma-4-26b-a4b-it
  temperature                  0
  maxOutputTokens              2048
  Batch size                   5 records per request
  Inter-batch pause            6 seconds
  Retry wait -- attempts 1-3   2 minutes
  Retry wait -- attempt 4+     5 minutes
  Response format              JSON array: [{"index": N, "<field>": "value"}]

temperature = 0 was chosen to maximise determinism. The batch size of 5 and the
6-second inter-batch pause keep request throughput within the free-tier rate limit
of 15 requests per minute.

On an API failure (HTTP 429 rate-limit or a server error), the affected rule waits
2 minutes before retry attempts 1-3 and 5 minutes from attempt 4 onward. During the
wait, a per-column countdown timer is shown alongside a manual "retry" button that
skips the remaining wait and triggers the next attempt immediately. Classification
can also be paused at any time.


Prompt design
--------------

Each classification dimension has its own independent prompt, containing only the
fields configured for that rule. This minimises token usage and allows prompts to
be refined independently. The model is instructed to return a JSON array only,
without markdown wrappers; a regex-based fallback parser recovers partial responses
when the primary JSON parse fails.

The following sections document the exact prompts used in the wind energy review.

================================================================================

DEFAULT CODING SCHEME (WIND ENERGY FORECASTING)

The five dimensions below are the built-in presets. They were designed for a
systematic review on wind energy forecasting and can be used as-is, modified, or
replaced.


DIMENSION 1 -- target: Predicted variable
------------------------------------------

  Method: regex+ai
  Input fields: Title, Author Keywords

Values:
  "velocidade do vento"   The proposed model's primary output is wind speed
  "potencia"              The model forecasts power output (any source) and does
                          not meet the wind speed criterion
  "outro"                 Any other output variable, no clear proposed model,
                          or not applicable

Regex rules (evaluated in order; first match wins):
  Pattern          Assigned value
  -------          --------------
  /wind speed/i    velocidade do vento
  /wind power/i    potencia
  (no match)       empty -> Phase 2

Design rationale. Only "wind power" triggers "potencia"; broader terms such as
"power output" or "power generation" generate false positives in papers that
discuss power as background context rather than as the forecasting target.

Prompt (exact string sent to the API):

  Voce e um especialista em ML.
  Analise o titulo e palavras-chave de cada artigo e classifique o campo abaixo:

  == target ==
  Variavel alvo do modelo proposto. Siga a HIERARQUIA abaixo em ordem:
  1. "velocidade do vento": o modelo tem velocidade do vento como variavel de saida
  2. "potencia": o modelo tem potencia como variavel de saida (qualquer fonte:
     eolica, solar, etc.) e NAO se enquadra na regra anterior
  3. "outro": outra variavel de saida, sem modelo proposto claro, ou nao aplicavel


DIMENSION 2 -- task: Primary research task
-------------------------------------------

  Method: regex+ai
  Input fields: Title, Author Keywords

Values:
  "previsao"              Forecasting of wind speed, power, or meteorological variables
  "otimizacao"            Scheduling, dispatch, storage, market bidding, grid management
  "avaliacao de recurso"  Wind potential assessment, Weibull fitting, site analysis
  "controle"              Wake control, pitch control, frequency control
  "modelagem de curva"    Power curve modelling
  "deteccao de anomalias" Anomaly detection, fault detection, SCADA data cleaning
  "geracao de dados"      Data augmentation, synthetic data generation
  "simulacao fisica"      CFD, WRF, or LES as the primary model
  "avaliacao de risco"    Risk assessment or uncertainty quantification as the
                          primary focus
  "revisao"               Systematic review, survey, benchmark, or comparative study
  "outro"                 Does not fit the above categories

Regex rules (evaluated in order; first match wins):
  Priority  Patterns                                           Assigned value
  --------  --------                                           --------------
  1         /systematic review/i, /literature survey/i        revisao
  2         /\bCFD\b/, /\bLES\b/, /\bWRF\b/                  simulacao fisica
  3         /anomaly detection/i, /fault detection/i,          deteccao de anomalias
            /fault diagnosis/i
  4         /data augmentation/i, /synthetic data/i            geracao de dados
  5         /risk assessment/i                                 avaliacao de risco
  6         /wake control/i, /pitch control/i,                 controle
            /frequency control/i
  7         /power curve/i                                     modelagem de curva
  8         /resource assessment/i, /wind potential/i          avaliacao de recurso
  9         /\bscheduling\b/i, /\bdispatch\b/i,               otimizacao
            /\barbitrage\b/i, /unit commitment/i
  10        /forecasting/i, /prediction/i                      previsao
  --        (no match)                                         empty -> Phase 2

Design rationale:
  - "otimizacao" is tested before "previsao" because optimisation papers frequently
    mention forecasting as a subcomponent; the reverse is not true.
  - "optimization" alone is excluded from the "otimizacao" triggers because it
    commonly refers to hyperparameter optimisation, not operational optimisation.
  - "SCADA" alone is excluded from "deteccao de anomalias" because SCADA data is
    used across multiple tasks, including forecasting.
  - Trigger terms are kept to at most two words to maximise match rate while
    preserving specificity; longer phrases are too infrequent to be useful.
  - The regex scope is restricted to title and author keywords, not the abstract or
    index keywords. These terms appear frequently in abstracts as background or
    baseline description rather than as the paper's primary contribution, reducing
    precision when the abstract is included.

Prompt (exact string sent to the API):

  Voce e um especialista em ML.
  Analise o titulo e palavras-chave de cada artigo e classifique o campo abaixo:

  == task ==
  Tarefa principal do artigo. Use EXATAMENTE uma das opcoes:
  - "previsao": forecasting de velocidade, potencia ou variaveis meteorologicas
  - "otimizacao": scheduling, dispatch, armazenamento, leilao, gestao, feature
    selection como foco
  - "avaliacao de recurso": potencial eolico, Weibull, analise de sitio
  - "controle": wake control, pitch control, controle de frequencia
  - "modelagem de curva": power curve modeling
  - "deteccao de anomalias": outlier detection, fault detection, limpeza SCADA
  - "geracao de dados": data augmentation, synthetic data
  - "simulacao fisica": CFD, WRF, LES como modelo principal
  - "avaliacao de risco": risk assessment, uncertainty quantification como foco
  - "revisao": systematic review, survey, benchmark, comparative study
  - "outro": nao se encaixa nas anteriores


DIMENSION 3 -- architecture: Architectural family
--------------------------------------------------

  Method: ai
  Input fields: Title, Abstract, Author Keywords, Index Keywords

Values are multi-label and combinable: a paper may receive several tags separated
by commas (e.g., "Transformer, Rede Recorrente"). Metaheuristics and training
paradigms (PSO, transfer learning, federated learning) are not architecture tags
-- they are classified under complementary_technique.

  Tag                  Description                                  Examples
  ---                  -----------                                  --------
  Transformer          Attention-based backbone as central          Informer, PatchTST,
                       mechanism                                    Crossformer, Autoformer,
                                                                    Mamba
  Rede Recorrente      Explicit temporal recurrence with gating     LSTM, GRU, BiLSTM,
                                                                    RNN, Elman, xLSTM
  Rede Convolucional   Local feature extraction via convolutions    CNN, TCN, ResNet,
                                                                    ConvLSTM, WaveNet
  Rede de Grafos       Models over graph structures                 GCN, GAT, AGCRN,
                                                                    DCRNN, STGCN
  MLP-based            Multi-layer perceptrons with specialised     N-BEATS, N-HiTS,
                       blocks                                       TSMixer, TiDE
  Ensemble             Combinations of multiple models or trees     XGBoost, LightGBM,
                                                                    Random Forest, CatBoost,
                                                                    Stacking
  Neuro-Fuzzy          Fuzzy inference combined with neural nets    ANFIS, FIS+NN
  LLM                  Large language models for time series        GPT, LLaMA
  Estatistico          Classical statistical models                 ARIMA, SARIMA,
                                                                    regression, Bayesian DLM
  Fisico               Physics-based or numerical simulation        NWP, WRF, CFD, LES
  Outro                Not classifiable above                       KAN, Diffusion Models,
                                                                    RL, GAM, Quantum NN
  -                    No clear proposed model                      --

Prompt (exact string sent to the API):

  Voce e um especialista em ML.
  Analise o titulo, palavras-chave e abstract de cada artigo e classifique o campo
  abaixo:

  == architecture ==
  Liste as familias arquiteturais do modelo PROPOSTO. Podem ser MULTIPLAS tags
  separadas por virgula.
  Use APENAS as opcoes abaixo -- inclua todas que compoem a arquitetura proposta:
  - "Transformer": backbone baseado em atencao (Transformer, Informer, PatchTST,
    Mamba, Crossformer, Autoformer)
  - "Rede Recorrente": LSTM, GRU, BiLSTM, RNN, Elman, xLSTM
  - "Rede Convolucional": CNN, TCN, ResNet, ConvLSTM, WaveNet
  - "Rede de Grafos": GCN, GAT, AGCRN, DCRNN, STGCN
  - "MLP-based": N-BEATS, N-HiTS, TSMixer, TiDE
  - "Ensemble": XGBoost, Random Forest, LightGBM, CatBoost, Stacking
  - "Neuro-Fuzzy": sistemas fuzzy + redes neurais (ANFIS, FIS+NN)
  - "LLM": Large Language Models para series temporais (GPT, LLaMA)
  - "Estatistico": puramente estatistico (ARIMA, SARIMA, regressao, Bayesian DLM)
  - "Fisico": puramente fisico (NWP, WRF, CFD, LES)
  - "Outro": nao classificavel (KAN, Diffusion, RL puro, GAM, Quantum NN)
  - "-": sem modelo proposto claro
  REGRAS: Metaheuristica e transfer learning NAO sao arquitetura -- vao em
  complementary_technique.


DIMENSION 4 -- model: Proposed model name
------------------------------------------

  Method: ai
  Input fields: Title, Abstract, Author Keywords, Index Keywords

The exact name or acronym of the proposed model (e.g., "DBANN",
"CEEMDAN+VMD+GRU", "PINN+Informer"). Returns "-" when no clear proposed model
is identified.

Prompt (exact string sent to the API):

  Voce e um especialista em ML.
  Analise o titulo, palavras-chave e abstract de cada artigo e classifique o campo
  abaixo:

  == model ==
  Nome/sigla EXATA do modelo proposto (ex: "DBANN", "CEEMDAN+VMD+GRU",
  "PINN+Informer").
  Use "-" se nao ha modelo proposto claro.


DIMENSION 5 -- complementary_technique: Complementary techniques
-----------------------------------------------------------------

  Method: ai
  Input fields: Title, Abstract, Author Keywords, Index Keywords

Techniques complementary to the primary architecture: optimisation algorithms,
training paradigms, and methodological strategies. Examples: "PSO",
"NSGA-III feature selection", "transfer learning", "federated learning",
"meta-learning", "knowledge distillation", "quantile regression", "Monte Carlo".
Multiple values are separated by commas; "-" when none apply.

Prompt (exact string sent to the API):

  Voce e um especialista em ML.
  Analise o titulo, palavras-chave e abstract de cada artigo e classifique o campo
  abaixo:

  == complementary_technique ==
  Tecnicas COMPLEMENTARES a arquitetura: otimizacao, paradigma de treinamento,
  estrategia metodologica.
  Exemplos: "PSO", "NSGA-III feature selection", "transfer learning", "federated
  learning", "meta-learning", "knowledge distillation", "quantile regression",
  "Monte Carlo".
  Use "-" se nao ha tecnica complementar relevante. Multiplas separadas por virgula.

================================================================================

SOURCE PROVENANCE

For each dimension configured as "regex" or "regex+ai", BIIA writes an additional
"<id>_source" column recording whether the value was assigned by "regex" or "ai".
This enables per-dimension audit of the relative coverage of each phase, and
supports quality assessment of the hybrid pipeline.


Output format
--------------

All original CSV columns are preserved. BIIA appends one column per active rule,
named by the rule's ID, followed by the corresponding _source column where
applicable.

Example output columns for the default presets:
  Title, Abstract, Author Keywords, Index Keywords, doi, year,
  architecture, model, complementary_technique,
  task, task_source,
  target, target_source

Example row:
  "Wind speed forecasting...","This paper proposes...","wind speed; LSTM; VMD",
  "10.xxx",2025,"Rede Recorrente, Rede Convolucional","VMD+BiLSTM","PSO",
  "previsao","regex","velocidade do vento","regex"

================================================================================

REPRODUCIBILITY

Input format
-------------

A CSV file with at least a "Title" column. When available, "Abstract",
"Author Keywords", and "Index Keywords" are used by the AI rules. Column names
are matched as provided (case-sensitive). Any additional columns are preserved
unchanged in the output.


Running the tool
-----------------

Online (recommended): https://tathianamb.github.io/biia/

Local static server:
  npx serve .
  -- or --
  python -m http.server

API key: a free Google Gemini API key is required (obtainable at
aistudio.google.com). The key is stored only in the browser's localStorage and
never transmitted beyond the Gemini API.

Rule persistence: active rules and the user rule library are stored in localStorage
and restored on reload, allowing classification sessions to be resumed without data
loss.


Fill modes
-----------

  Mode              Behaviour
  ----              ---------
  Fill empty only   Skips records that already have a value -- enables resuming
                    interrupted sessions
  Overwrite all     Reprocesses every record -- use after revising the taxonomy
                    or prompt

================================================================================

LIMITATIONS

- Partial determinism. temperature = 0 reduces but does not eliminate output
  variability across runs, particularly for ambiguous records.

- Restricted regex scope. The regex phase covers only titles and author keywords,
  sacrificing recall for precision; ambiguous titles are deferred to the AI phase.

- Dependence on an external model. Classification accuracy is contingent on the
  behaviour of the Gemini API; changes in model policy or output format between
  runs may introduce inconsistencies.

- No automated inter-rater reliability. The tool does not compute agreement
  statistics (e.g., Cohen's kappa); quality validation requires manual sampling.

- Closed taxonomy for "target" and "task". Papers that do not fit the defined
  values are assigned "outro", which may aggregate heterogeneous cases.

================================================================================

LICENSE

MIT -- free to use, modify, and distribute with attribution.

================================================================================

CITATION

If you use BIIA in a published systematic review, please cite the software
repository:

  Barchi, T. BIIA: Bibliography + AI -- a browser-based tool for AI-assisted
  systematic literature review classification. GitHub, 2025.
  Available at: https://github.com/tathianamb/biia
