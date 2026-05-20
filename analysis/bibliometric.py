import re
import itertools
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import networkx as nx
import plotly.graph_objects as go
import nltk
from wordcloud import WordCloud
from nltk.corpus import stopwords

nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)


def top_authors(df, top_n=10, col='Authors'):
    all_authors = []
    for authors in df[col].dropna():
        all_authors.extend([a.strip() for a in str(authors).split(';')])
    return pd.Series(all_authors).value_counts().head(top_n)


def top_institutions(df, top_n=15, col='Institution'):
    return df[col].str.split(';').explode().str.strip().value_counts().head(top_n)


def top_journals(df, top_n=15, col='Source title'):
    return df[col].str.lower().value_counts().head(top_n)


def top_countries(df, top_n=None, col='Country'):
    s = df[col].str.split(';').explode().str.strip()
    vc = s.value_counts()
    return vc.head(top_n) if top_n else vc


def keywords_cooccurrence(df, outdir, col='Author Keywords', top_n=30):
    def ajustar_rotulo(rotulo):
        palavras = rotulo.split()
        return '\n'.join(palavras) if len(palavras) > 1 else rotulo

    df = df.copy()
    df['KW_list'] = (df[col].str.lower()
                     .str.replace(r'[^a-z; ]', ' ', regex=True)
                     .str.replace(r'  +', ' ', regex=True)
                     .str.split(';'))
    df['KW_list'] = df['KW_list'].apply(
        lambda lst: [w.strip() for w in lst] if isinstance(lst, list) else [])

    pares = []
    for palavras in df['KW_list']:
        pares.extend(itertools.combinations(sorted(set(palavras)), 2))

    contagem = Counter(pares).most_common(top_n)

    with open(outdir / 'contagem_coocorrencias.txt', 'w') as fout:
        for (p1, p2), peso in contagem:
            fout.write(f'({p1}/{p2}): {peso}\n')

    grafo = nx.Graph()
    for (p1, p2), peso in contagem:
        grafo.add_edge(p1, p2, weight=np.sqrt(peso))

    if grafo.number_of_nodes() == 0:
        print("keywords_cooccurrence: sem co-ocorrências suficientes para gerar rede.")
        return

    grau_nos = dict(grafo.degree())
    maior_no = max(grafo.degree, key=lambda x: x[1])[0]
    font_size_labels = {no: max(grau_nos[no] * 0.7, 14) for no in grafo.nodes()}

    shells = [[maior_no], list(set(grafo.nodes()) - {maior_no})]
    pos = nx.shell_layout(grafo, nlist=shells)
    pos = {no: (x * 40, y * 40) for no, (x, y) in pos.items()}
    node_size = [50 * grafo.degree(n) for n in grafo.nodes()]

    plt.figure(figsize=(10, 10))
    nx.draw_networkx_nodes(grafo, pos, node_size=node_size, node_color="#55c667ff", alpha=0.8)
    nx.draw_networkx_edges(grafo, pos,
                           width=[d['weight'] for (_, _, d) in grafo.edges(data=True)],
                           edge_color="#3cbb75ff", alpha=0.3)
    for no, (x, y) in pos.items():
        plt.text(x, y, s=ajustar_rotulo(no), horizontalalignment='center',
                 verticalalignment='center', fontsize=font_size_labels[no], linespacing=0.7)
    plt.axis('off')
    plt.savefig(outdir / "keywords_cooccurrence.png", dpi=150, bbox_inches='tight')
    plt.close()


def analyze_freq(df, outdir, column='Abstract'):
    stop_words = set(stopwords.words('english'))
    tokens = df[column].str.findall(r'\b[a-zA-Z]+\b').explode().tolist()
    filtered = [w for w in tokens if w.lower() not in stop_words]
    freq = Counter(filtered)
    wordcloud = WordCloud(width=800, height=400, background_color='white', colormap='viridis',
                          max_words=200, contour_color='steelblue').generate_from_frequencies(freq)
    wordcloud.to_file(str(outdir / 'wordcloud.png'))
    return sorted(freq.items(), key=lambda x: x[1], reverse=True)[:20]


def wordtree(df, outdir, coluna_texto='Abstract', termo_central='system'):
    de, para, frases = [], [], []
    for texto in df[coluna_texto].dropna().astype(str):
        frase = ""
        palavras = re.split(r'\W+', texto.lower())
        try:
            index = palavras.index(termo_central.lower())
            if index > 2:
                de.append(f"-3. {palavras[index - 3]}")
                para.append(f"-2. {palavras[index - 2]}")
                frase += ' ' + palavras[index - 3]
            if index > 1:
                de.append(f"-2. {palavras[index - 2]}")
                para.append(f"-1. {palavras[index - 1]}")
                frase += ' ' + palavras[index - 2]
            if index > 0:
                de.append(f"-1. {palavras[index - 1]}")
                para.append(f"+0. {palavras[index]}")
                frase += ' ' + palavras[index - 1]
            frase += ' ' + palavras[index]
            if index < len(palavras) - 1:
                de.append(f"+0. {palavras[index]}")
                para.append(f"+1. {palavras[index + 1]}")
                frase += ' ' + palavras[index + 1]
            if index < len(palavras) - 2:
                de.append(f"+1. {palavras[index + 1]}")
                para.append(f"+2. {palavras[index + 2]}")
                frase += ' ' + palavras[index + 2]
            if index < len(palavras) - 3:
                de.append(f"+2. {palavras[index + 2]}")
                para.append(f"+3. {palavras[index + 3]}")
                frase += ' ' + palavras[index + 3]
            frases.append(frase)
        except ValueError:
            continue

    with open('frases_termo_central.txt', 'w') as fout:
        for s in frases:
            fout.write(s + '\n')

    df_trans = pd.DataFrame({"De": de, "Para": para})
    df_agrup = df_trans.groupby(["De", "Para"], sort=False).size().reset_index(name='Contagem')
    labels = list(pd.unique(df_agrup[['De', 'Para']].values.ravel('K')))
    sources = df_agrup['De'].apply(labels.index).tolist()
    targets_idx = df_agrup['Para'].apply(labels.index).tolist()
    values = df_agrup['Contagem'].tolist()

    fig = go.Figure(go.Sankey(
        node=dict(pad=15, thickness=1,
                  line=dict(color="rgba(190,190,190,1)", width=0.5),
                  label=[l[3:] for l in labels], color="rgba(0,0,0,0)"),
        link=dict(source=sources, target=targets_idx, value=values,
                  color=[mcolors.to_hex(c)
                         for c in sns.color_palette("crest", n_colors=2 * len(sources))])
    ))
    fig.update_layout(title_text=f"Sankey Chart para '{termo_central}'",
                      font_family="Times New Roman", font_size=20)
    fig.write_image(str(outdir / f"13_wordtree_{termo_central}.png"))
