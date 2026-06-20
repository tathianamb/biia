# Visão geral do projeto

BIIA (bibliografia + ia) é um aplicativo de navegador de arquivo único (`index.html`) para classificação assistida por IA de literatura acadêmica. Ele recebe um CSV de artigos, aplica regras de classificação definidas pelo usuário via regex e/ou a API Gemini, e exporta um CSV enriquecido. 

Implantado automaticamente no GitHub Pages a partir do branch `main`. A URL ao vivo é `https://tathianamb.github.io/biia/`.

## Fluxo de Dados

`allRows[]` é a única fonte de verdade, um array de objetos de linha mutado in-place — stats, tabela e download derivam todos dele.

1. **Entrada.** O usuário carrega um CSV (input de arquivo ou drag-and-drop) → `FileReader.readAsText(utf-8)` → `parseCSV()` → `allRows[]` (objetos de linha indexados pelos cabeçalhos do CSV). `onCSVLoad()` define `csvHeaders` a partir de `Object.keys(rows[0])` e chama `ensureRuleColumns()` para criar as colunas `<id>` e `<id>_source` vazias. ⚠️ `parseCSV` faz `text.split(/\r?\n/)` **antes** de tratar aspas, então um campo com quebra de linha entre aspas desalinha as colunas a partir dali.
2. **Regras.** O usuário define `userRules[]` via os cards da UI (cada regra: `id`, `method`, `inputCols`, `regexText`, `prompt`, `mode`, `multi`, `active`). As regras ativas **não** persistem entre reloads — `persistRules()` é um no-op; só a `ruleLibrary` (`biia_rulelib_v1`) sobrevive. Essa **biblioteca de regras reutilizáveis** é o que distingue as duas listas: o botão ★ em cada card chama `saveRuleToLibrary()`, persistindo uma cópia da regra (por `id`, com upsert) em `biia_rulelib_v1`. O painel "minhas regras" lista as salvas como chips; clicar em uma chama `addRuleFromLibrary()` para adicioná-la a `userRules` (filtrando seus `inputCols` para os cabeçalhos do CSV carregado), e o × chama `removeFromLibrary()`. `toggleLibraryPanel()`/`buildLibraryChips()` controlam a abertura e a renderização do painel. Não há presets embutidos: a ferramenta é genérica e só lista as regras que o usuário salvou.
3. **Classificação** (`startClassification`). Regras em `mode: "all"` têm `<id>` e `<id>_source` pré-limpos antes de tudo. A fase de regex roda de forma síncrona em todas as linhas; a fase de IA roda as regras em paralelo via `Promise.all(aiRules.map(runAIRule))`, mas dentro de cada regra os lotes (de linhas ainda vazias) são processados sequencialmente — um `await` por lote, com pausa de 6 s entre eles.
4. **Gravação.** Os resultados escrevem direto em `allRows[i][rule.id]` e `allRows[i][rule.id + "_source"]` (`"regex"` ou `"ai"`). Na fase de IA, cada item do lote carrega seu `globalIdx`, que mantém a resposta alinhada à linha original mesmo fora de ordem.
5. **Saída.** `downloadCSV()` re-serializa `allRows` para CSV — colunas originais, depois colunas de regra, depois colunas `<id>_source` — escapando aspas (`"` → `""`) e salvando via uma URI `data:` em base64 sob o nome de arquivo fixo `biia-output.csv`.

## Seleção de Modelo

`GEMINI_MODELS` define os modelos disponíveis, na ordem de fallback inicial: `gemini-3.1-flash-lite`, `gemma-4-31b-it`, `gemma-4-26b-a4b-it`. Eles populam o dropdown e servem de base para os dois modos abaixo.

- `pinnedModel`: modelo selecionado pelo usuário no dropdown, armazenado no `localStorage` como `biia_pinned_model`. Quando há um pin, `callModel` usa **exclusivamente** esse modelo — sem fallback: se ele falhar, o erro sobe direto para o `runWithBackoff` (que fará retry no mesmo modelo). No carregamento, `initModel` o valida contra `GEMINI_MODELS` — um pin persistido que não está mais na lista é silenciosamente descartado e o app reverte para automático.
- `activeModel`: último modelo que respondeu com sucesso, armazenado como `biia_model`
- Modo automático: tenta modelos até um ter sucesso, mas a ordem **não é fixa** — `callModel` promove `activeModel` para o início (`[activeModel, ...GEMINI_MODELS.filter(≠activeModel)]`). A ordem de `GEMINI_MODELS` só é usada literalmente na primeira chamada (ou sempre que ainda não há um `activeModel`); uma vez que um modelo tem sucesso, ele é tentado primeiro em toda chamada subsequente.

## Regras de Classificação

**Modo de preenchimento (`mode`) e a pré-limpeza do `"all"`:** cada regra tem um `mode` que decide o que fazer com células **já preenchidas** ao (re)classificar. `"empty"` (padrão, "Preencher apenas vazios") pula qualquer linha cuja célula daquela regra já tem valor — é o que torna a sessão retomável após uma pausa. `"all"` ("Sobrescrever tudo") recalcula a coluna inteira do zero. O detalhe não óbvio é *como* o `"all"` descarta o conteúdo antigo: `startClassification` zera tanto `<id>` quanto `<id>_source` de antemão — **antes** da fase de regex — em vez de sobrescrever célula a célula. Assim, numa regra `regex+ai` em `"all"`, a regex volta a rodar em todas as linhas e a IA cobre os vazios, recalculando ambas as fases a partir do vazio.

### Fase 1 (regex)

Para cada regra `regex` ou `regex+ai`, `applyRuleRegex()` testa cada linha de forma síncrona; correspondências são gravadas imediatamente. Por padrão (`multi: true`) a regra é **multivalorada**: todo padrão que casa contribui com seu valor, juntados por `", "` (ordem preservada, deduplicada). Com `multi: false` apenas o primeiro padrão que casa vence.

**Sintaxe.** Cada linha é parseada por `parseRegexLines()` como `/padrão/flags > valor` — o separador `>` foi escolhido por ser fácil de digitar e não ser metacaractere de regex, então nunca colide com o corpo do padrão. A divisão ocorre no **primeiro `>` após a barra de fechamento**; o padrão é sempre greedy até a última `/` antes do `>`. As `flags` são as letras opcionais após a barra de fechamento que ajustam como o padrão casa; sem flags explícitas, o padrão usa `i` por padrão. Só são reconhecidas as flags que o regex de parsing aceita (as do JavaScript):

| Flag | Nome | Efeito |
|------|------|--------|
| `i` | *ignore case* | ignora maiúsculas/minúsculas (default quando nenhuma flag é dada) |
| `g` | *global* | casa todas as ocorrências, não só a primeira |
| `m` | *multiline* | `^` e `$` passam a casar início/fim de cada linha, não só do texto todo |
| `s` | *dotAll* | o `.` passa a casar também quebras de linha |
| `u` | *unicode* | trata o padrão como sequência de code points Unicode |
| `y` | *sticky* | só casa a partir da posição exata de `lastIndex` |

Na prática, como `applyRuleRegex` faz apenas um teste booleano (`regex.test`), `i` é a única com efeito frequente; as demais raramente alteram o resultado de "casou ou não" sobre títulos/keywords.

Exemplo — uma regra `arquitetura` com os padrões:

```
/transformer|attention/i > Transformer
/lstm|gru|recurrent/i    > Rede Recorrente
/cnn|convolutional/i     > CNN
```

Para um artigo cujo título seja *"A CNN-LSTM hybrid for wind speed forecasting"*:
- com `multi: true` (padrão), o segundo e o terceiro padrões casam → célula recebe `"Rede Recorrente, CNN"` (na ordem das regras);
- com `multi: false`, só o primeiro que casa vale → célula recebe `"Rede Recorrente"`.

**Casos não permitidos.** Linhas que não se encaixam na forma acima são tratadas assim:

- **Vírgula no valor é proibida** quando `multi` está ligado, porque nada faz split na vírgula a jusante: o valor é armazenado literalmente e `updateStats()`, a tabela e a filtragem tratam cada célula como uma string única. Assim `/wind speed/i > velocidade, vento` vira o valor único `"velocidade, vento"`, que se torna seu próprio bucket — contado e filtrado como distinto de `"velocidade"` (`toggleFilter`/`renderTable` casam a célula inteira, `r[col] === val`) e indistinguível de dois valores em qualquer consumidor que faça split por vírgula. Para emitir dois rótulos, use **duas linhas** (`/wind speed/i > velocidade` e `/wind speed/i > vento`).
- **Sem delimitadores `/.../`**: `wind speed > x` **não casa** e a linha é **silenciosamente ignorada**. O padrão precisa estar entre barras.
- **Regex inválido**: um padrão que faz `new RegExp` lançar (ex.: `/[/i > x`) é capturado pelo `catch` e a linha é **silenciosamente ignorada** — não há mensagem de erro na UI.
- **Flag não reconhecida**: qualquer letra fora de `gimsuy` faz a linha inteira não casar o padrão `/.../flags > valor` e ser descartada como malformada — não há validação dedicada de flags, é o mesmo caminho dos itens acima.
- **Linhas em branco e comentários** (começando com `#`) são ignorados de propósito.
- **`>` extra no valor** é permitido (vira parte do valor, pois o split é no primeiro `>`), mas evite por clareza.

### Fase 2 (IA)

Cada regra `ai` ou `regex+ai` cria uma stream assíncrona independente (`runAIRule`); as linhas que continuam vazias após a fase de regex são agrupadas em lotes de 5 (`BATCH = 5`) e enviadas ao Gemini com `temperature: 0` e `maxOutputTokens: 2048` (`generationConfig` em `classifyBatchForRule`), com pausa de 6 segundos entre lotes.

**Retry e backoff.** `runWithBackoff()` envolve cada lote com retry automático — espera de 2 min para as tentativas 1–3, 5 min a partir da 4ª. O retry é **ilimitado**: é um loop `while (true)` sem número máximo de tentativas, então os valores de 2/5 min são a *espera entre* tentativas, não um limite de quantas; ele nunca desiste por conta própria, só para em caso de sucesso ou quando o usuário aperta **Pausar**. Durante a espera, `setPhaseRetry()` mostra uma contagem regressiva por coluna (`⚠️ tentativa N · m:ss`) com um botão **retry** manual; clicar nele chama `skipBackoffWait(phaseId)` (define `skipWait[phaseId] = true`), que interrompe a contagem antecipadamente e dispara a próxima tentativa imediatamente.

**Pausar e retomar.** A classificação pode ser pausada a qualquer momento via `pauseClassification()` (`stopFlag`). Após pausar, o botão **Pausar** reverte para **▶ Classificar**, e clicar nele de novo *retoma* em vez de reiniciar: graças ao `mode` (ver [Modo de preenchimento](#regras-de-classificação)), uma regra `"empty"` só reprocessa as linhas que ficaram vazias quando a pausa ocorreu, enquanto uma regra `"all"` recomeça do zero.

**Resposta e parsing.** O modelo é solicitado a responder com um array JSON `[{"index": N, "<rule.id>": "valor"}]`, onde `index` referencia a posição no lote — `classifyBatchForRule` o resolve de volta para a linha global via `batchItems[r.index]`. O parsing trata tanto JSON válido quanto respostas parciais/malformadas via fallback por regex.

Exemplo — uma regra `arquitetura` com método `ai`, entradas `Title` e `Abstract`, e prompt *"Classifique a arquitetura de rede neural usada no artigo."* Para um lote de 2 artigos, `buildPromptForRule` monta:

```
Classifique a arquitetura de rede neural usada no artigo.

Responda APENAS com JSON válido, sem markdown:
[{"index":0,"arquitetura":"..."}]

Artigos:
[0]
Title: A CNN-LSTM hybrid for wind speed forecasting
Abstract: -

---

[1]
Title: Attention-based forecasting of wind power
Abstract: -
```

E o modelo responde com o array indexado pela posição no lote:

```json
[{"index":0,"arquitetura":"CNN-LSTM"},{"index":1,"arquitetura":"Transformer"}]
```

Cada `index` é resolvido para a linha global correspondente (`batchItems[0]`, `batchItems[1]`) e gravado em `allRows[...].arquitetura`, com `arquitetura_source = "ai"`.

# Limitações

## Limitações de dados e interface

- **Parser CSV ingênuo:** `parseCSV` divide o texto em linhas (`text.split(/\r?\n/)`) **antes** de tratar as aspas, então um campo com quebra de linha dentro de aspas (`"linha1\nlinha2"`) é cortado no meio e desalinha as colunas a partir daquela linha. Exports de Scopus/Web of Science cujos abstracts contêm quebras de linha entre aspas são afetados; nesses casos, normalize o CSV (remover quebras internas) antes de carregar.
- **Cabeçalhos de CSV duplicados se sobrescrevem:** como cada linha vira um objeto (`row[h.trim()] = cols[j]`), duas colunas com o mesmo nome colapsam — a segunda esmaga a primeira e `csvHeaders` (`Object.keys`) lista o nome uma só vez. A coluna duplicada some sem aviso. Renomeie cabeçalhos repetidos antes de carregar.
- **Colisão entre nome de regra e coluna existente:** se uma regra recebe um `id` igual ao de uma coluna já presente no CSV (ex.: regra `idioma` num CSV que já tem `idioma`), a classificação grava em `allRows[i][rule.id]` **sobre** a coluna original, e o download a emite como coluna de regra — o valor de origem é perdido silenciosamente. Use nomes de saída que não colidam com os cabeçalhos de entrada.
- **Regras ativas não persistem:** `persistRules()` é um no-op (ver [Fluxo de Dados](#fluxo-de-dados), passo 2), então fechar ou recarregar a aba descarta toda a configuração de `userRules` — só a biblioteca (`biia_rulelib_v1`) sobrevive. Em sessões longas, salve as regras importantes na biblioteca (★) antes de sair.
- **Visualização limitada a 300 linhas:** `renderTable` exibe no máximo `MAX = 300` linhas (com um rodapé "mostrando 300 de N"); o filtro e a busca operam sobre o conjunto todo, mas só os 300 primeiros resultados aparecem na tela. A classificação e o download (`downloadCSV`) sempre processam **todas** as linhas — o limite é apenas da tabela na UI.

## Limitações de qualidade da classificação

Estas afetam diretamente *o rótulo atribuído* — sua validade, consistência ou completude:

- **Determinismo parcial:** `temperature=0` reduz mas não elimina variabilidade entre execuções, especialmente em casos ambíguos.
- **Dependência do modelo externo:** a classificação depende da disponibilidade e comportamento da API Gemini; mudanças na política de saída do modelo entre execuções podem introduzir inconsistências.
- **Escopo regex configurável:** a fase de regex usa apenas as colunas que o usuário seleciona em `inputCols`; o equilíbrio entre precisão e recall depende dessa escolha. Restringir a entrada a poucas colunas de alto sinal aumenta a precisão, mas deixa mais casos ambíguos para a IA cobrir.
- **Taxonomia fechada (quando o usuário a define):** regras com vocabulário controlado classificam casos que não se enquadram em um rótulo genérico (ex.: `"outro"`), o que pode agrupar casos heterogêneos. Isso depende inteiramente das regras configuradas pelo usuário — a ferramenta não impõe nenhuma taxonomia.
- **A resposta da IA não é validada contra um vocabulário:** `buildPromptForRule` injeta apenas `rule.prompt` livre + os artigos; nada obriga o modelo a escolher dentro de um conjunto de rótulos, e o que ele devolve é gravado como veio (`classifyBatchForRule` aceita qualquer `r[rule.id]` definido). Se o prompt não enumera as opções, o modelo cria rótulos livres; mesmo que enumere, grafias variáveis ("CNN-LSTM" vs "CNN/LSTM" vs "híbrido CNN-LSTM") fragmentam os buckets de `updateStats`/filtro, que casam strings exatas. Mitigação: enumere os rótulos no prompt e peça resposta exatamente igual a um deles — mas a conformidade não é garantida pela ferramenta.
- **A IA não revisa o que a regex já preencheu:** em `regex+ai`, a fase de IA só processa linhas que ficaram vazias após a regex (`if ((row[r.id]||"").trim()) continue` em `runAIRule`). Um match de regex incorreto ou parcial — ex.: um termo que aparece como *contexto*, não como a contribuição do artigo — nunca é corrigido pela IA; a regex sempre vence onde casa. Para essas dimensões, prefira `ai` puro ou estreite os padrões.
- **Pegadinhas de regex (falsos positivos):** o casamento é por substring via `regex.test` — `/cnn/i` casa "cnn" dentro de palavras maiores; use `\b` (fronteira de palavra) explicitamente quando quiser o termo isolado. Além disso, `inputCols` é juntado por espaço antes do teste, então um padrão multi-palavra pode casar atravessando a fronteira entre duas colunas (última palavra de uma + primeira da seguinte). Restrinja `inputCols` e ancore os padrões para evitar.
- **Protocolo de IA por lote:** os 5 artigos do lote vão no mesmo prompt, então pode haver contaminação de contexto entre eles (a rotulação de um item influenciada por outro) — `temperature: 0` reduz, mas não elimina. O alinhamento depende do `index` devolvido: um `index` repetido sobrescreve silenciosamente a entrada anterior, e um `index` esperado que o modelo omita deixa a linha vazia (reprocessada na próxima execução). Um valor vazio (`""`) devolvido pela IA também conta como "não classificado" e será reprocessado — logo, casos ambíguos podem **oscilar** entre execuções.
- **Truncamento silencioso por `maxOutputTokens`:** o limite de 2048 tokens de saída é fixo e um batch de 5 artigos pode estourá-lo, produzindo um JSON truncado. O parser cai então no fallback por regex (`clean.match(/\{[^{}]*"index"...\}/g)`), que recupera apenas os objetos completos — itens cortados no fim da resposta são **descartados sem aviso**, e essas linhas permanecem vazias (sendo reprocessadas em uma re-execução). Reduzir o `BATCH` ou encurtar os prompts mitiga o problema (ambos são constantes no código, não ajustáveis pela UI).
