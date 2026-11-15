"""Three ways to guess which tiles a viewer will need, and how tiles are picked.

The stream is cut into one-second segments. For the segment that starts at
second s, the system must decide `horizon` seconds earlier which `budget` tiles
to fetch in high quality. A predictor gives every tile a score for that segment
and the system fetches the top-scoring tiles.

- own motion: assume the viewer keeps looking where they look now. The score is
  the viewer's window at second s - horizon.
- crowd: the score is the average window of k earlier viewers during second s
  of the same video. They watched earlier, so their whole trace is known and
  the horizon does not matter.
- blend: a weighted sum of the two.

All three scores are "share of a window in each tile", so each sums to 1 and
they can be mixed directly.
"""
from __future__ import annotations

import numpy as np

from src import geometry

SEGMENT_S = 1
HORIZONS = (1, 2, 5)


def segment_weights(weights: np.ndarray, hz: int, segment_s: int = SEGMENT_S) -> np.ndarray:
    """(viewers, ticks, tiles) -> (viewers, segments, tiles): the average window over
    each whole segment. A segment with no samples at all stays NaN."""
    per = hz * segment_s
    n = weights.shape[1] // per
    blocks = weights[:, :n * per].reshape(weights.shape[0], n, per, weights.shape[2])
    present = ~np.isnan(blocks[..., 0])
    total = np.where(present[..., None], blocks, 0).sum(axis=2)
    count = present.sum(axis=2)[..., None]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(count > 0, total / count, np.nan).astype(np.float32)


def instant_weights(weights: np.ndarray, hz: int, segment_s: int = SEGMENT_S) -> np.ndarray:
    """(viewers, ticks, tiles) -> (viewers, segments, tiles): the window at the instant
    each segment starts. A missing instant takes the last known window before it."""
    per = hz * segment_s
    n = weights.shape[1] // per
    out = weights[:, :n * per:per].copy()
    for s in range(1, n):
        gap = np.isnan(out[:, s, 0])
        out[gap, s] = out[gap, s - 1]
    return out


def own_motion_scores(instant: np.ndarray, horizon: int) -> np.ndarray:
    """Score for segment s is the viewer's own window at s - horizon. The first
    `horizon` segments have nothing to go on and are NaN."""
    out = np.full_like(instant, np.nan)
    out[:, horizon:] = instant[:, :-horizon]
    return out


def crowd_scores(segments: np.ndarray, group: np.ndarray) -> np.ndarray:
    """(viewers, segments, tiles) and the group's row numbers -> (segments, tiles):
    the group's average window in each segment, skipping members with no data there."""
    g = segments[np.asarray(group)]
    present = ~np.isnan(g[..., 0])
    total = np.where(present[..., None], g, 0).sum(axis=0)
    count = np.maximum(present.sum(axis=0), 1)[..., None]
    return total / count


def blend_scores(own: np.ndarray, crowd: np.ndarray, own_weight: float) -> np.ndarray:
    """own is (viewers, segments, tiles), crowd is (segments, tiles)."""
    return own_weight * own + (1 - own_weight) * crowd[None]


_NEIGHBOURS: dict = {}


def neighbour_matrix(rows: int = geometry.ROWS, cols: int = geometry.COLS) -> np.ndarray:
    """(tiles, tiles) matrix with 1 where two tiles touch, corners included. The frame
    wraps left to right but not top to bottom."""
    if (rows, cols) not in _NEIGHBOURS:
        a = np.zeros((rows * cols, rows * cols))
        for r in range(rows):
            for c in range(cols):
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if (dr or dc) and 0 <= r + dr < rows:
                            a[r * cols + c, (r + dr) * cols + (c + dc) % cols] = 1.0
        _NEIGHBOURS[(rows, cols)] = a
    return _NEIGHBOURS[(rows, cols)]


def neighbour_sum(scores: np.ndarray, rows: int = geometry.ROWS, cols: int = geometry.COLS) -> np.ndarray:
    """For each tile, the summed score of the eight tiles around it."""
    return np.asarray(scores, dtype=np.float64) @ neighbour_matrix(rows, cols)


def choose_tiles(scores: np.ndarray, budget: int, rows: int = geometry.ROWS, cols: int = geometry.COLS) -> np.ndarray:
    """Top `budget` tiles by score as a boolean mask of the same shape.

    A small crowd leaves many tiles with a score of exactly zero. Ties are broken
    in favour of tiles next to high-scoring ones, then by tile number, so a spare
    tile pads the edge of the predicted window instead of landing somewhere random.
    Rows that are all NaN (nothing to predict from) choose nothing."""
    s = np.asarray(scores, dtype=np.float64)
    missing = np.isnan(s).any(axis=-1)
    s = np.where(missing[..., None], 0.0, s)
    key = s + 1e-4 * neighbour_sum(s, rows, cols) - 1e-9 * np.arange(s.shape[-1])
    order = np.argpartition(-key, budget - 1, axis=-1)[..., :budget]  # keys are distinct, so the set is unique
    mask = np.zeros(s.shape, dtype=bool)
    np.put_along_axis(mask, order, True, axis=-1)
    mask[missing] = False
    return mask
