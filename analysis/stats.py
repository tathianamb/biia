import numpy as np
from scipy import stats


def wilson_ci(p, n, z=1.96):
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = (z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2))) / denom
    return center - margin, center + margin


def chi2_agrupado(series_rev, series_unrev, min_expected=5):
    """
    Qui-quadrado com agrupamento de categorias raras.
    Categorias cuja frequência esperada < min_expected são fundidas em 'outras'.
    Retorna chi2, p, dof, n_cats_originais, n_cats_apos_agrupamento, aviso.
    """
    cats = series_rev.index.union(series_unrev.index).tolist()
    obs_rev   = np.array([series_rev.get(c, 0)   for c in cats])
    obs_unrev = np.array([series_unrev.get(c, 0) for c in cats])
    contingency = np.array([obs_rev, obs_unrev])
    _, _, _, expected = stats.chi2_contingency(contingency)
    keep = (expected >= min_expected).all(axis=0)
    agg_rev   = obs_rev[keep].tolist()   + ([obs_rev[~keep].sum()]   if (~keep).any() else [])
    agg_unrev = obs_unrev[keep].tolist() + ([obs_unrev[~keep].sum()] if (~keep).any() else [])
    n_orig = len(cats)
    n_apos = len(agg_rev)
    cont_agg = np.array([agg_rev, agg_unrev])
    mask_zero = cont_agg.sum(axis=0) > 0
    cont_agg = cont_agg[:, mask_zero]
    chi2_val, p_val, dof, _ = stats.chi2_contingency(cont_agg)
    agrupou = n_apos < n_orig
    aviso = (f'categorias raras agrupadas: {n_orig} -> {n_apos} grupos'
             if agrupou else 'sem agrupamento necessario')
    return chi2_val, p_val, dof, n_orig, n_apos, aviso
