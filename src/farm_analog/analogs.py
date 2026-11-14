"""Climate analog matching (sigma dissimilarity, Mahony et al. 2017)."""
import numpy as np
from scipy.stats import chi2
from sklearn.decomposition import PCA


def sigma_dissimilarity(target_future, target_icv, candidates, min_var=1e-6):
    """Distance from a farm's future climate to every candidate cell, in sigma units.

    target_future: (n_vars,) future climate at the farm
    target_icv:    (n_years, n_vars) the farm's historical yearly values
    candidates:    (n_cells, n_vars) present-day climate of every search cell

    Below ~2 sigma is a good analog; above ~4 sigma is effectively a novel climate.
    """
    mu, sd = target_icv.mean(0), target_icv.std(0)
    pca = PCA().fit((target_icv - mu) / sd)
    keep = pca.explained_variance_ > min_var

    def proj(x):
        z = pca.transform((x - mu) / sd)[:, keep]
        return z / np.sqrt(pca.explained_variance_[keep])

    d = np.linalg.norm(proj(candidates) - proj(np.asarray(target_future)[None]), axis=1)
    # Upper-tail probability in k dimensions, mapped to the equivalent 1-D sigma.
    # Survival functions (sf/isf) keep large distances finite where cdf/ppf round to 1 -> inf;
    # the floor caps extreme values at ~37 sigma, which is "novel climate" either way.
    tail = chi2.sf(d**2, df=keep.sum())
    return np.sqrt(chi2.isf(np.maximum(tail, 1e-300), df=1))
