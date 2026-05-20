import matplotlib
matplotlib.use('Agg')

import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from analysis.io import load_data, check_duplicate_dois, coalesce, split_list
from analysis.plots import value_counts_table, explode_counts, save_bar
from analysis.predicted import (
    normalize_labels,
    plot_coverage,
    plot_accuracy_by_source,
    plot_accuracy_by_task_category,
    plot_accuracy_by_target_category,
    plot_confusion_task,
    plot_confusion_target,
    plot_discrepancies,
    save_part1_csvs,
    compute_stratified_analysis,
    plot_representativeness,
    save_part2_csvs,
)

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)
pd.set_option('display.max_colwidth', None)

INPUT = Path(sys.argv[1] if len(sys.argv) > 1 else "biia-output-final.csv")
OUTDIR = Path("./outputs/predicted")
STATSDIR = Path("./outputs/stats")
OUTDIR.mkdir(parents=True, exist_ok=True)
STATSDIR.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

LABEL_TRIOS = [("task_checked", "task_predicted", "task_source"),
               ("target_checked", "target_predicted", "target_source")]


def main(df):
    df["task"]      = df.apply(lambda r: coalesce(r, LABEL_TRIOS[0]), axis=1)
    df["target"]    = df.apply(lambda r: coalesce(r, LABEL_TRIOS[1]), axis=1)
    df["arch_list"] = df["architecture"].apply(split_list)
    df["compl_list"] = df["complementary_technique"].apply(split_list)

    # ── Qualidade das labels ──────────────────────────────────────────────────
    df = normalize_labels(df)
    rev_task   = df[df['task_chk_n']   != ''].copy()
    rev_target = df[df['target_chk_n'] != ''].copy()
    n_total = len(df)
    n_rt    = len(rev_task)
    n_rg    = len(rev_target)

    print(f'Total: {n_total} | task revisados: {n_rt} ({100*n_rt/n_total:.1f}%) '
          f'| target revisados: {n_rg} ({100*n_rg/n_total:.1f}%)')

    plot_coverage(df, OUTDIR)
    plot_accuracy_by_source(rev_task, rev_target, OUTDIR)
    plot_accuracy_by_task_category(rev_task, OUTDIR)
    plot_accuracy_by_target_category(rev_target, OUTDIR)
    ct   = plot_confusion_task(rev_task, OUTDIR)
    ct_t = plot_confusion_target(rev_target, OUTDIR)
    disc_task, disc_target = plot_discrepancies(rev_task, rev_target, OUTDIR)
    save_part1_csvs(rev_task, rev_target, disc_task, disc_target, ct, ct_t, OUTDIR)

    stat_df, regex_df = compute_stratified_analysis(df, STATSDIR)
    plot_representativeness(regex_df, stat_df, STATSDIR)
    save_part2_csvs(df, OUTDIR)

    print("Done. Outputs in", OUTDIR.resolve(), "and", STATSDIR.resolve())


if __name__ == "__main__":
    df = load_data(INPUT)
    df = check_duplicate_dois(df)
    main(df)
