"""How well a set of high-quality tiles served a viewer.

coverage      share of the viewer's real window, over one segment, that fell on
              high-quality tiles. 1 is perfect, 0 means all they saw was low quality.
poor seconds  seconds per minute of video in which coverage was below a threshold.
worst 10%     the average of a number over the worst-served tenth of viewers.
"""
from __future__ import annotations

import numpy as np

POOR_BELOW = 0.5
WORST_SHARE = 0.10


def coverage(chosen: np.ndarray, actual: np.ndarray) -> np.ndarray:
    """chosen: boolean (..., tiles). actual: the viewer's real window share per tile,
    same shape or broadcastable. Returns (...) coverage, NaN where the window is unknown."""
    return np.where(chosen, actual, 0).sum(axis=-1) + np.where(np.isnan(actual[..., 0]), np.nan, 0.0)


def mean_coverage(cov: np.ndarray, axis: int = -1) -> np.ndarray:
    return np.nanmean(cov, axis=axis)


def poor_seconds_per_minute(cov: np.ndarray, below: float = POOR_BELOW, axis: int = -1) -> np.ndarray:
    """Share of known segments with coverage under `below`, scaled to seconds per minute."""
    known = ~np.isnan(cov)
    poor = (cov < below) & known
    return 60.0 * poor.sum(axis=axis) / np.maximum(known.sum(axis=axis), 1)


def tail_mean(values, share: float = WORST_SHARE, worst: str = "low") -> float:
    """Average over the worst `share` of the values.

    With 16 viewers, a tenth is 1.6 viewers. I take the worst viewer in full and
    0.6 of the next one, so the answer does not jump when the group size changes.
    worst="low" means small values are bad (coverage); "high" means large values
    are bad (poor seconds)."""
    v = np.asarray(values, float)
    v = np.sort(v[~np.isnan(v)])
    if worst == "high":
        v = v[::-1]
    take = share * len(v)
    whole = int(np.floor(take))
    weights = np.zeros(len(v))
    weights[:whole] = 1.0
    if whole < len(v):
        weights[whole] = take - whole
    return float((v * weights).sum() / weights.sum())
