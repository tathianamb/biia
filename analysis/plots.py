import matplotlib.pyplot as plt
import seaborn as sns


def value_counts_table(series, name, top=None):
    vc = series.value_counts()
    if top:
        vc = vc.head(top)
    return vc.rename_axis(name).reset_index(name="count")


def explode_counts(df, col, name, top=None):
    s = df[col].explode().dropna()
    s = s[s != ""]
    return value_counts_table(s, name, top)


def save_bar(table, x, y, title, fname, outdir, rotate=30):
    plt.figure(figsize=(10, 5))
    sns.barplot(data=table, x=x, y=y)
    plt.title(title)
    plt.xticks(rotation=rotate, ha="right")
    plt.tight_layout()
    plt.savefig(outdir / fname, dpi=150)
    plt.close()
