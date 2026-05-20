import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import seaborn as sns

from analysis.io import load_data, check_duplicate_dois, coalesce, split_list
from analysis.plots import value_counts_table, save_bar
from analysis.trends import arch_x_complementary, arch_trend, complementary_cooccurrence

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', None)

INPUT = Path(sys.argv[1] if len(sys.argv) > 1 else "biia-output-final.csv")
OUTDIR = Path("./outputs/combined")
OUTDIR.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

LABEL_TRIOS   = [("task_checked", "task_predicted", "task_source"),
                 ("target_checked", "target_predicted", "target_source")]
TASK_FILTER   = "previsão"
TARGET_FILTER = "velocidade do vento"


def main(df):
    df["task"]       = df.apply(lambda r: coalesce(r, LABEL_TRIOS[0]), axis=1)
    df["target"]     = df.apply(lambda r: coalesce(r, LABEL_TRIOS[1]), axis=1)
    df["arch_list"]  = df["architecture"].apply(split_list)
    df["compl_list"] = df["complementary_technique"].apply(split_list)
    df = df[(df["task"] == TASK_FILTER) & (df["target"] == TARGET_FILTER)].copy()
    print(f"Corpus filtrado: {len(df)} papers (task={TASK_FILTER!r}, target={TARGET_FILTER!r})")
    if df.empty:
        print("Nenhum paper encontrado após o filtro. Verifique TASK_FILTER e TARGET_FILTER.")
        return

    # overview
    overview = {
        "n_papers":         len(df),
        "year_min":         int(df["Year"].min()),
        "year_max":         int(df["Year"].max()),
        "n_sources":        df["Source title"].nunique(),
        "median_citations": float(df["Cited by"].median()),
    }
    pd.DataFrame([overview]).to_csv(OUTDIR / "overview.csv", index=False)

    # top citados
    top_cited = df.sort_values("Cited by", ascending=False).head(20)[
        ["Year", "Cited by", "Title", "Source title", "DOI", "architecture"]
    ]
    top_cited.to_csv(OUTDIR / "top_cited.csv", index=False)

    # gap signals
    arch_total  = Counter(a for lst in df["arch_list"] for a in lst if a)
    rare_arch   = sorted([a for a, n in arch_total.items() if n <= 2])
    recent      = df[df["Year"] >= df["Year"].max() - 1]
    recent_arch = Counter(a for lst in recent["arch_list"] for a in lst if a)
    emerging    = [a for a, _ in recent_arch.most_common(10)]

    with open(OUTDIR / "gap_signals.md", "w", encoding="utf-8") as fout:
        fout.write("# Gap signals\n\n")
        fout.write(f"**Corpus:** {overview['n_papers']} papers "
                   f"(task={TASK_FILTER!r}, target={TARGET_FILTER!r}), "
                   f"{overview['year_min']}–{overview['year_max']}\n\n")
        fout.write("## Architectures rarely used (≤2 papers)\n")
        fout.write(", ".join(rare_arch) or "(none)")
        fout.write("\n\n## Emerging architectures (top in last 2 years)\n")
        fout.write(", ".join(emerging) or "(none)")
        fout.write("\n")

    # tendências e paradigmas dominantes
    arch_x_complementary(df, OUTDIR)
    arch_trend(df, OUTDIR)
    complementary_cooccurrence(df, OUTDIR)

    print("Done. Outputs in", OUTDIR.resolve())


if __name__ == "__main__":
    df = load_data(INPUT)
    df = check_duplicate_dois(df)
    main(df)
