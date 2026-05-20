import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from .stats import wilson_ci, chi2_agrupado


def normalize_labels(df):
    def norm(s):
        return s.str.strip().str.lower().str.split('(').str[0].str.strip()

    df = df.copy()
    df['task_pred_n']    = norm(df['task_predicted'])
    df['task_chk_n']     = norm(df['task_checked'])
    df['target_pred_n']  = norm(df['target_predicted'])
    df['target_chk_n']   = norm(df['target_checked'])
    df['task_isequal']   = df['task_isequal'].str.strip().str.upper()
    df['target_isequal'] = df['target_isequal'].str.strip().str.upper()
    df['task_final']     = df['task_chk_n'].where(df['task_chk_n']   != '', df['task_pred_n'])
    df['target_final']   = df['target_chk_n'].where(df['target_chk_n'] != '', df['target_pred_n'])
    df['any_ai']         = (df['task_source'] == 'ai') | (df['target_source'] == 'ai')
    df['both_regex']     = ~df['any_ai']
    return df


# ── Parte 1: acurácia das predições ──────────────────────────────────────────

def plot_coverage(df, outdir):
    n_total = len(df)
    n_rt = (df['task_chk_n']   != '').sum()
    n_rg = (df['target_chk_n'] != '').sum()

    fig, ax = plt.subplots(figsize=(6, 4))
    cov = pd.DataFrame({
        'Revisados':     [n_rt,           n_rg],
        'Não revisados': [n_total - n_rt, n_total - n_rg],
    }, index=['task', 'target'])
    cov.plot(kind='bar', stacked=True, ax=ax, color=['#1976D2', '#CFD8DC'], edgecolor='white')
    ax.set_title('Cobertura de revisão humana')
    ax.set_ylabel('papers')
    ax.set_xticklabels(ax.get_xticklabels(), rotation=0)
    for i, (rev, tot) in enumerate(zip([n_rt, n_rg], [n_total, n_total])):
        ax.text(i, rev / 2, f'{100*rev/tot:.1f}%', ha='center', va='center',
                color='white', fontweight='bold', fontsize=11)
    plt.tight_layout()
    plt.savefig(outdir / 'coverage.png', dpi=150)
    plt.close()
    print('1/11 coverage ok')

def plot_accuracy_by_source(rev_task, rev_target, outdir):
    rows = []
    for label, sub, eq_col, src_col in [
        ('task',   rev_task,   'task_isequal',   'task_source'),
        ('target', rev_target, 'target_isequal', 'target_source')]:
        for src in ['regex', 'ai']:
            g = sub[sub[src_col] == src]
            if len(g):
                rows.append({'label': label, 'source': src, 'n': len(g),
                             'acuracia': (g[eq_col] == 'TRUE').mean()})
    acc_src = pd.DataFrame(rows)

    fig, ax = plt.subplots(figsize=(7, 4))
    x = np.arange(2)
    w = 0.35
    for i, (src, color) in enumerate([('regex', '#1976D2'), ('ai', '#F57C00')]):
        vals = acc_src[acc_src['source'] == src]['acuracia'].values * 100
        ns   = acc_src[acc_src['source'] == src]['n'].values
        rects = ax.bar(x + i * w - w / 2, vals, w, label=src, color=color)
        for r, v, n in zip(rects, vals, ns):
            ax.text(r.get_x() + r.get_width() / 2, v + 1.5,
                    f'{v:.1f}%\n(n={n})', ha='center', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(['task', 'target'])
    ax.set_ylim(0, 120)
    ax.set_ylabel('Acurácia (%)')
    ax.legend()
    plt.tight_layout()
    plt.savefig(outdir / 'accuracy_by_source.png', dpi=150)
    plt.close()
    print('5/11 accuracy by source ok')


def plot_accuracy_by_task_category(rev_task, outdir):
    cat_acc = (rev_task.groupby('task_chk_n')
               .apply(lambda g: pd.Series({
                   'n': len(g),
                   'acuracia': (g['task_isequal'] == 'TRUE').mean()
               }))
               .reset_index()
               .sort_values('acuracia'))

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#EF9A9A' if v < 0.85 else '#A5D6A7' for v in cat_acc['acuracia']]
    bars = ax.bar(cat_acc['task_chk_n'], cat_acc['acuracia'] * 100, color=colors)
    for bar, n, v in zip(bars, cat_acc['n'], cat_acc['acuracia'] * 100):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1,
                f'{v:.1f}%\n(n={int(n)})', ha='center', fontsize=8)
    ax.set_ylim(0, 125)
    ax.set_ylabel('Acurácia (%)')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    plt.savefig(outdir / 'accuracy_by_task_category.png', dpi=150)
    plt.close()
    print('6/11 accuracy by task category ok')


def plot_accuracy_by_target_category(rev_target, outdir):
    cat_acc_t = (rev_target.groupby('target_chk_n')
                 .apply(lambda g: pd.Series({
                     'n': len(g),
                     'acuracia': (g['target_isequal'] == 'TRUE').mean()
                 }))
                 .reset_index()
                 .sort_values('acuracia'))

    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['#EF9A9A' if v < 0.85 else '#A5D6A7' for v in cat_acc_t['acuracia']]
    bars = ax.bar(cat_acc_t['target_chk_n'], cat_acc_t['acuracia'] * 100, color=colors)
    for bar, n, v in zip(bars, cat_acc_t['n'], cat_acc_t['acuracia'] * 100):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 1,
                f'{v:.1f}%\n(n={int(n)})', ha='center', fontsize=8)
    ax.set_ylim(0, 125)
    ax.set_ylabel('Acurácia (%)')
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    plt.savefig(outdir / 'accuracy_by_target_category.png', dpi=150)
    plt.close()
    print('7/11 accuracy by target category ok')


def plot_confusion_task(rev_task, outdir):
    ct = pd.crosstab(rev_task['task_chk_n'], rev_task['task_pred_n'])
    fig, ax = plt.subplots(figsize=(11, 8))
    sns.heatmap(ct, annot=True, fmt='d', cmap='Blues', ax=ax, linewidths=0.5)
    ax.set_xlabel('PREDICTED')
    ax.set_ylabel('GROUND TRUTH')
    plt.tight_layout()
    plt.savefig(outdir / 'confusion_task.png', dpi=150)
    plt.close()
    print('8/11 confusion task ok')
    return ct


def plot_confusion_target(rev_target, outdir):
    ct_t = pd.crosstab(rev_target['target_chk_n'], rev_target['target_pred_n'])
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(ct_t, annot=True, fmt='d', cmap='Blues', ax=ax, linewidths=0.5)
    ax.set_xlabel('PREDICTED')
    ax.set_ylabel('GROUND TRUTH')
    plt.tight_layout()
    plt.savefig(outdir / 'confusion_target.png', dpi=150)
    plt.close()
    print('9/11 confusion target ok')
    return ct_t


def plot_discrepancies(rev_task, rev_target, outdir):
    disc_task = (rev_task[rev_task['task_isequal'] == 'FALSE']
                 .groupby(['task_pred_n', 'task_chk_n']).size()
                 .reset_index(name='count').sort_values('count', ascending=False))
    disc_target = (rev_target[rev_target['target_isequal'] == 'FALSE']
                   .groupby(['target_pred_n', 'target_chk_n']).size()
                   .reset_index(name='count').sort_values('count', ascending=False))

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, data, pred, chk, title in [
        (axes[0], disc_task.head(12),   'task_pred_n',   'task_chk_n',   'task'),
        (axes[1], disc_target.head(10), 'target_pred_n', 'target_chk_n', 'target')]:
        labels = [f'{p}  ->  {c}' for p, c in zip(data[pred], data[chk])]
        ax.barh(labels[::-1], data['count'].values[::-1], color='#EF5350')
        ax.set_xlabel('quantidade')
        ax.set_title(title)
    plt.tight_layout()
    plt.savefig(outdir / 'discrepancies.png', dpi=150)
    plt.close()
    print('10/11 discrepancies ok')
    return disc_task, disc_target

def save_part1_csvs(rev_task, rev_target, disc_task, disc_target, ct, ct_t, outdir):
    summary_rows = []
    for label, sub, eq_col, src_col in [
        ('task',   rev_task,   'task_isequal',   'task_source'),
        ('target', rev_target, 'target_isequal', 'target_source')]:
        for src in ['regex', 'ai', 'total']:
            g = sub if src == 'total' else sub[sub[src_col] == src]
            summary_rows.append({
                'label':        label,
                'source':       src,
                'n_revisados':  len(g),
                'concordantes': (g[eq_col] == 'TRUE').sum(),
                'discordantes': (g[eq_col] == 'FALSE').sum(),
                'acuracia':     round((g[eq_col] == 'TRUE').mean(), 4) if len(g) else None
            })
    pd.DataFrame(summary_rows).to_csv(outdir / 'accuracy_summary.csv', index=False)
    disc_task.rename(columns={'task_pred_n': 'predicted', 'task_chk_n': 'checked'}).to_csv(
        outdir / 'discrepancies_task.csv', index=False)
    disc_target.rename(columns={'target_pred_n': 'predicted', 'target_chk_n': 'checked'}).to_csv(
        outdir / 'discrepancies_target.csv', index=False)
    ct.to_csv(outdir / 'confusion_task.csv')
    ct_t.to_csv(outdir / 'confusion_target.csv')
    print('\nCSVs salvos.')
    print('\n--- Resumo de acuracia ---')
    print(pd.DataFrame(summary_rows).to_string(index=False))


# ── Parte 2: labels finais + relevância estatística ───────────────────────────

def compute_stratified_analysis(df, outdir):
    stat_rows = []
    print('\n--- Acurácia por estrato ---')

    ai_df = df[df['any_ai']].copy()
    for label, eq_col in [('task', 'task_isequal'), ('target', 'target_isequal')]:
        n = len(ai_df)
        p = (ai_df[eq_col] == 'TRUE').mean()
        stat_rows.append({
            'label': label, 'estrato': 'any_ai (populacao)',
            'n_total_estrato': n, 'n_revisados': n, 'cobertura_pct': 100.0,
            'acuracia': round(p, 4),
            'ci95_lower': None, 'ci95_upper': None, 'margem_erro_95pp': None,
            'n_minimo_moe5pct': None, 'suficiente': 'N/A (populacao completa)',
            'chi2_representatividade': None, 'p_valor_chi2': None,
            'amostra_representativa': 'N/A (populacao completa)'
        })
        print(f'  any_ai / {label}: acuracia={p:.1%} (n={n}, valor exato)')

    regex_df = df[df['both_regex']].copy()
    for label, pred_col, chk_col, eq_col in [
        ('task',   'task_pred_n',   'task_chk_n',   'task_isequal'),
        ('target', 'target_pred_n', 'target_chk_n', 'target_isequal')]:
        rev   = regex_df[regex_df[chk_col] != '']
        unrev = regex_df[regex_df[chk_col] == '']
        n_tot = len(regex_df)
        n_rev = len(rev)
        p = (rev[eq_col] == 'TRUE').mean()
        lo, hi = wilson_ci(p, n_rev)
        n_min = int(np.ceil(1.96**2 * p * (1 - p) / 0.05**2))
        chi2_val, p_chi, dof, n_orig, n_apos, aviso = chi2_agrupado(
            rev[pred_col].value_counts(), unrev[pred_col].value_counts())
        stat_rows.append({
            'label': label, 'estrato': 'both_regex (amostra)',
            'n_total_estrato': n_tot, 'n_revisados': n_rev,
            'cobertura_pct': round(100 * n_rev / n_tot, 1),
            'acuracia': round(p, 4),
            'ci95_lower': round(lo, 4), 'ci95_upper': round(hi, 4),
            'margem_erro_95pp': round((hi - lo) / 2 * 100, 2),
            'n_minimo_moe5pct': n_min,
            'suficiente': 'SIM' if n_rev >= n_min else 'NAO',
            'chi2_representatividade': round(chi2_val, 4),
            'p_valor_chi2': round(p_chi, 4),
            'graus_liberdade': dof,
            'nota_chi2': aviso,
            'amostra_representativa': 'SIM (p>=0.05)' if p_chi >= 0.05 else 'NAO (p<0.05)'
        })
        print(f'  both_regex / {label}: acuracia={p:.1%} IC95%=[{lo:.1%},{hi:.1%}] '
              f'moe=±{(hi-lo)/2*100:.1f}pp | chi2 p={p_chi:.4f} ({aviso})')

    stat_df = pd.DataFrame(stat_rows)
    stat_df.to_csv(outdir / 'statistical_relevance_stratified.csv', index=False)
    print(stat_df.to_string(index=False))
    return stat_df, regex_df

def plot_representativeness(regex_df, stat_df, outdir):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, label, pred_col, chk_col in [
        (axes[0], 'task',   'task_pred_n',   'task_chk_n'),
        (axes[1], 'target', 'target_pred_n', 'target_chk_n')]:
        rev_r   = regex_df[regex_df[chk_col] != '']
        unrev_r = regex_df[regex_df[chk_col] == '']
        cats = regex_df[pred_col].value_counts().index.tolist()
        pct_rev   = [rev_r[pred_col].value_counts(normalize=True).get(c, 0) * 100 for c in cats]
        pct_unrev = [unrev_r[pred_col].value_counts(normalize=True).get(c, 0) * 100 for c in cats]
        x = np.arange(len(cats))
        w = 0.35
        ax.bar(x - w / 2, pct_rev,   w, label=f'revisados (n={len(rev_r)})',       color='#1976D2', alpha=0.85)
        ax.bar(x + w / 2, pct_unrev, w, label=f'nao revisados (n={len(unrev_r)})', color='#90A4AE', alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(cats, rotation=30, ha='right', fontsize=8)
        ax.set_ylabel('%')
        p_chi = stat_df[(stat_df['label'] == label) & (stat_df['estrato'] == 'both_regex (amostra)')]['p_valor_chi2'].values[0]
        rep   = stat_df[(stat_df['label'] == label) & (stat_df['estrato'] == 'both_regex (amostra)')]['amostra_representativa'].values[0]
        ax.set_title(f'{label} (regex-only): revisados vs nao revisados\nchi2 p={p_chi:.4f} — {rep}')
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(outdir / 'representativeness_regex.png', dpi=150)
    plt.close()
    print('15 representativeness regex chart ok')


def save_part2_csvs(df, outdir):
    df[['task_final']].value_counts().rename_axis('task_final').reset_index(name='count').to_csv(
        outdir / 'task_final_counts.csv', index=False)
    df[['target_final']].value_counts().rename_axis('target_final').reset_index(name='count').to_csv(
        outdir / 'target_final_counts.csv', index=False)
    print('\nParte 2 concluida. Todos os outputs em', outdir.resolve())
