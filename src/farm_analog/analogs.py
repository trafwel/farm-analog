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
    target_future = np.asarray(target_future, dtype=float)
    target_icv = np.asarray(target_icv, dtype=float)
    candidates = np.asarray(candidates, dtype=float)
    if target_icv.ndim != 2 or candidates.ndim != 2 or target_future.ndim != 1:
        raise ValueError('Expected a future vector and two data matrices.')
    if target_icv.shape[1] != len(target_future) or candidates.shape[1] != len(target_future):
        raise ValueError('Climate feature counts must match.')
    if target_icv.shape[0] <= target_icv.shape[1] or min_var <= 0:
        raise ValueError('Need more historical years than features and a positive variance threshold.')
    if not all(np.isfinite(x).all() for x in (target_future, target_icv, candidates)):
        raise ValueError('Climate inputs must be finite; missing data cannot be scored.')
    mu, sd = target_icv.mean(0), target_icv.std(0)
    if np.any(sd <= 0):
        raise ValueError('Historical climate features must have nonzero variability.')
    pca = PCA().fit((target_icv - mu) / sd)
    keep = pca.explained_variance_ > min_var
    if not keep.all():
        raise ValueError('Historical covariance is singular or unstable; revise climate features.')

    def proj(x):
        z = pca.transform((x - mu) / sd)[:, keep]
        return z / np.sqrt(pca.explained_variance_[keep])

    d = np.linalg.norm(proj(candidates) - proj(np.asarray(target_future)[None]), axis=1)
    # Upper-tail probability in k dimensions, mapped to the equivalent 1-D sigma.
    # Survival functions (sf/isf) keep large distances finite where cdf/ppf round to 1 -> inf;
    # the floor caps extreme values at ~37 sigma, which is "novel climate" either way.
    tail = chi2.sf(d**2, df=keep.sum())
    return np.sqrt(chi2.isf(np.maximum(tail, 1e-300), df=1))
