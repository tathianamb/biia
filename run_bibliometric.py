import sys
from pathlib import Path

import pandas as pd
import seaborn as sns

from analysis.io import load_data, check_duplicate_dois, coalesce, split_list
from analysis.plots import save_bar
from analysis.bibliometric import (top_authors, top_institutions, top_journals,
                                    top_countries, keywords_cooccurrence, analyze_freq)

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', None)

INPUT = Path(sys.argv[1] if len(sys.argv) > 1 else "biia-output-final.csv")
OUTDIR = Path("./outputs/bibliometric")
OUTDIR.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

LABEL_TRIOS  = [("task_checked", "task_predicted", "task_source"),
                ("target_checked", "target_predicted", "target_source")]
TASK_FILTER   = "previsão"
TARGET_FILTER = "velocidade do vento"


def main(df):
    df["task"]   = df.apply(lambda r: coalesce(r, LABEL_TRIOS[0]), axis=1)
    df["target"] = df.apply(lambda r: coalesce(r, LABEL_TRIOS[1]), axis=1)
    df = df[(df["task"] == TASK_FILTER) & (df["target"] == TARGET_FILTER)].copy()
    print(f"Corpus filtrado: {len(df)} papers (task={TASK_FILTER!r}, target={TARGET_FILTER!r})")
    if df.empty:
        print("Nenhum paper encontrado após o filtro. Verifique TASK_FILTER e TARGET_FILTER.")
        return

    # distribuição temporal
    by_year = df.groupby("Year").size().reset_index(name="papers")
    by_year.to_csv(OUTDIR / "papers_per_year.csv", index=False)
    save_bar(by_year, "Year", "papers", "Papers per year", "papers_per_year.png", OUTDIR, rotate=0)

    # frequência de keywords
    kw_series = (df["Author Keywords"].fillna("")
                 .str.lower().str.split(";").explode().str.strip())
    kw_series = kw_series[kw_series != ""]
    kw = kw_series.value_counts().head(40).reset_index()
    kw.columns = ["keyword", "count"]
    kw.to_csv(OUTDIR / "keywords.csv", index=False)
    save_bar(kw.head(20), "keyword", "count", "Top author keywords", "keywords.png", OUTDIR)

    # rede de co-ocorrência de keywords
    keywords_cooccurrence(df, OUTDIR)

    # frequência de palavras nos abstracts + wordcloud
    if "Abstract" in df.columns:
        word_freq = analyze_freq(df, OUTDIR, column='Abstract')
        pd.DataFrame(word_freq, columns=["word", "count"]).to_csv(
            OUTDIR / "word_frequency.csv", index=False)

    # sumários bibliométricos
    top_authors(df).rename_axis("author").reset_index(name="count").to_csv(
        OUTDIR / "top_authors.csv", index=False)
    top_journals(df).rename_axis("journal").reset_index(name="count").to_csv(
        OUTDIR / "top_journals.csv", index=False)
    if "Country" in df.columns:
        top_countries(df).rename_axis("country").reset_index(name="count").to_csv(
            OUTDIR / "top_countries.csv", index=False)
    if "Institution" in df.columns:
        top_institutions(df).rename_axis("institution").reset_index(name="count").to_csv(
            OUTDIR / "top_institutions.csv", index=False)

    print("Done. Outputs in", OUTDIR.resolve())


if __name__ == "__main__":
    df = load_data(INPUT)
    df = check_duplicate_dois(df)
    main(df)
