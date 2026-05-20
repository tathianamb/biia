import itertools
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx


def arch_x_complementary(df, outdir):
    """Matriz de frequência: arquitetura × técnica complementar."""
    exp = (df.explode("arch_list")
             .explode("compl_list")
             .reset_index(drop=True))
    exp = exp[(exp["arch_list"] != "") & (exp["compl_list"] != "")]

    if exp.empty:
        print("arch_x_complementary: sem dados para cruzar.")
        return

    ct = pd.crosstab(exp["arch_list"], exp["compl_list"])
    ct = ct.loc[(ct > 2).any(axis=1), (ct > 2).any(axis=0)]
    ct.to_csv(outdir / "arch_x_complementary.csv")

    fig, ax = plt.subplots(figsize=(max(6, 0.8 * ct.shape[1] + 1),
                                    max(4, 0.5 * ct.shape[0] + 1)))
    sns.heatmap(ct, annot=True, fmt="d", cmap="YlOrRd", cbar=True,
                linewidths=0.3, ax=ax)
    ax.set_xlabel("Técnica complementar")
    ax.set_ylabel("Arquitetura")
    plt.tight_layout()
    plt.savefig(outdir / "arch_x_complementary.png", dpi=150)
    plt.close()
    print("arch_x_complementary ok")


def arch_trend(df, outdir):
    """Evolução temporal das arquiteturas: linhas por arquitetura, X=ano, Y=papers."""
    exp = df.explode("arch_list").reset_index(drop=True)
    exp = exp[(exp["arch_list"] != "") & exp["Year"].notna()].copy()
    exp["Year"] = exp["Year"].astype(int)

    if exp.empty:
        print("arch_trend: sem dados.")
        return

    pivot = pd.crosstab(exp["Year"], exp["arch_list"])
    pivot = pivot.loc[:, pivot.max(axis=0) > 20]
    pivot.to_csv(outdir / "arch_trend.csv")

    HIGHLIGHT = {
        "rede recorrente":    ("#1976D2", "o"),
        "rede convolucional": ("#E53935", "s"),
        "transformer":        ("#43A047", "^"),
        "ensemble":           ("#8E24AA", "D"),
    }
    GRAY = "#BBBBBB"
    gray_markers = ['v', 'H', '8', 'P', 'X', '*', 'p', 'h', '<', '>', 'd']

    others     = [a for a in pivot.columns if a not in HIGHLIGHT]
    highlights = [a for a in HIGHLIGHT if a in pivot.columns]

    fig, ax = plt.subplots(figsize=(13, 6))

    # demais arquiteturas em cinza (fundo)
    for i, arch in enumerate(others):
        ax.plot(pivot.index, pivot[arch],
                label=arch,
                color=GRAY,
                marker=gray_markers[i % len(gray_markers)],
                linewidth=1.2,
                markersize=9,
                alpha=0.6,
                zorder=2)

    # arquiteturas destacadas em cor (frente)
    for arch in highlights:
        color, marker = HIGHLIGHT[arch]
        ax.plot(pivot.index, pivot[arch],
                label=arch,
                color=color,
                marker=marker,
                linewidth=2.2,
                markersize=7,
                zorder=5)

    # legenda: destacadas no topo, cinzas abaixo
    handles, labels = ax.get_legend_handles_labels()
    top_idx   = [labels.index(a) for a in highlights if a in labels]
    other_idx = [i for i, l in enumerate(labels) if l not in highlights]
    order     = top_idx + other_idx
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=10, framealpha=0.7)

    ax.set_xlabel("Ano")
    ax.set_ylabel("Nº de papers")
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.savefig(outdir / "arch_trend.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("arch_trend ok")


def complementary_cooccurrence(df, outdir, top_n=30):
    """Co-ocorrência de técnicas complementares: combinações presentes e ausentes."""
    pares = []
    for tecnicas in df["compl_list"]:
        unique = [t for t in tecnicas if t]
        pares.extend(itertools.combinations(sorted(set(unique)), 2))

    if not pares:
        print("complementary_cooccurrence: nenhum par encontrado.")
        return

    contagem   = Counter(pares)
    top_pares  = contagem.most_common(top_n)

    # CSV dos top pares
    cooc_df = pd.DataFrame(
        [(p1, p2, n) for (p1, p2), n in top_pares],
        columns=["tecnica_1", "tecnica_2", "count"]
    )
    cooc_df.to_csv(outdir / "complementary_cooccurrence.csv", index=False)

    # matriz completa (zeros = combinações ausentes)
    all_tecnicas = sorted(set(t for lst in df["compl_list"] for t in lst if t))
    matrix = pd.DataFrame(0, index=all_tecnicas, columns=all_tecnicas)
    for (p1, p2), n in contagem.items():
        matrix.loc[p1, p2] = n
        matrix.loc[p2, p1] = n
    matrix = matrix.loc[(matrix > 1).any(axis=1), (matrix > 1).any(axis=0)]
    matrix.to_csv(outdir / "complementary_cooccurrence_matrix.csv")

    # heatmap da matriz (0 = ausente)
    if not matrix.empty:
        n = max(matrix.shape)
        _, ax = plt.subplots(figsize=(max(6, 0.7 * n + 1), max(5, 0.6 * n + 1)))
        sns.heatmap(matrix, annot=True, fmt="d", cmap="YlOrRd",
                    linewidths=0.5, ax=ax, square=True)
        plt.tight_layout()
        plt.savefig(outdir / "complementary_cooccurrence_matrix.png", dpi=150)
        plt.close()
    else:
        print("complementary_cooccurrence: matriz vazia após filtro, heatmap não gerado.")

    # rede dos top pares
    def ajustar_rotulo(r):
        palavras = r.split()
        return '\n'.join(palavras) if len(palavras) > 2 else r

    grafo = nx.Graph()
    for (p1, p2), peso in top_pares:
        grafo.add_edge(p1, p2, weight=np.sqrt(peso))

    grau_nos   = dict(grafo.degree())
    maior_no   = max(grafo.degree, key=lambda x: x[1])[0]
    font_sizes = {no: max(grau_nos[no] * 0.7, 12) for no in grafo.nodes()}
    shells     = [[maior_no], list(set(grafo.nodes()) - {maior_no})]
    pos        = nx.shell_layout(grafo, nlist=shells)
    pos        = {no: (x * 40, y * 40) for no, (x, y) in pos.items()}
    node_size  = [50 * grafo.degree(n) for n in grafo.nodes()]

    plt.figure(figsize=(10, 10))
    nx.draw_networkx_nodes(grafo, pos, node_size=node_size, node_color="#5e4fa2", alpha=0.8)
    nx.draw_networkx_edges(grafo, pos,
                           width=[d["weight"] for (_, _, d) in grafo.edges(data=True)],
                           edge_color="#9e9ac8", alpha=0.4)
    for no, (x, y) in pos.items():
        plt.text(x, y, s=ajustar_rotulo(no), horizontalalignment="center",
                 verticalalignment="center", fontsize=font_sizes[no], linespacing=0.7)
    plt.axis("off")
    plt.title("Rede de co-ocorrência — técnicas complementares")
    plt.savefig(outdir / "complementary_cooccurrence_network.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("complementary_cooccurrence ok")
