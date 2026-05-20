import re
import pandas as pd


def load_data(path):
    df = pd.read_csv(path, sep=",", dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c]]
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    df["Cited by"] = pd.to_numeric(df["Cited by"], errors="coerce").fillna(0).astype(int)
    return df


def check_duplicate_dois(df, doi_col='DOI', report_path='duplicated_dois.csv'):
    has_doi = df[doi_col].notna() & (df[doi_col] != '')
    mask = has_doi & df.duplicated(subset=[doi_col], keep=False)
    duplicates = df[mask].sort_values(doi_col)
    if duplicates.empty:
        print("Nenhum DOI duplicado encontrado.")
        return df
    duplicates.to_csv(report_path, index=False)
    print(f"{len(duplicates)} registros com DOI duplicado encontrados. "
          f"Relatório salvo em '{report_path}'.")
    to_remove = has_doi & df.duplicated(subset=[doi_col], keep='first')
    df_clean = df[~to_remove].reset_index(drop=True)
    print(f"{to_remove.sum()} registro(s) removido(s). "
          f"Total restante: {len(df_clean)}.")
    return df_clean


def coalesce(row, cols):
    for c in cols:
        v = (row.get(c) or "").strip()
        if v and v.lower() not in {"nan", "-", "none"}:
            return v.lower()
    return ""


def split_list(s):
    if not s or s.strip() in {"-", ""}:
        return []
    return [x.strip().lower() for x in re.split(r"[;,]", s) if x.strip() and x.strip() != "-"]
