"""Viewing style: how a person tends to watch, measured on other videos.

Three numbers per viewer and video:

- head speed: how far the view direction moves in one second, in degrees,
  averaged over the video. Measured over a full second so that sensor jitter
  does not count as movement.
- exploration: entropy, in bits, of which tile the centre of the view sits in
  over time. Zero means the viewer never left one tile.
- on the crowd: the share of the viewer's window that falls on the 16 tiles the
  other viewers of that video watch most, second by second. This is "share of
  time on the most-watched region".

Videos differ a lot (a boxing match pins everyone to one spot), so each number
is turned into a z-score among the 48 viewers of that video. A viewer's style
for a given test video is the average z-score over the other videos. The test
video is never part of it.

Three ways to pick a group of k from a pool, all blind to the test video:

- random: any k.
- mixed: cluster the pool into k style clusters (k-means) and take the viewer
  nearest the centre of each. This is the "deliberately mixed group".
- typical: the k viewers who stay on the crowd most. This is a control. If it
  does as well as mixed, the gain comes from picking conformists, not variety.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from src import geometry, metrics, predict

FEATURES = ("head_speed", "exploration", "on_crowd")
REGION_TILES = 16


def head_speed(q: np.ndarray, hz: int) -> np.ndarray:
    """(viewers, ticks, 4) -> (viewers,): mean degrees moved per second."""
    f = geometry.forward(q)
    step = geometry.angle_between(f[:, hz:], f[:, :-hz])
    return np.nanmean(step, axis=1)


def exploration(q: np.ndarray) -> np.ndarray:
    """(viewers, ticks, 4) -> (viewers,): entropy in bits of the view-centre tile."""
    f = geometry.forward(q)
    out = np.zeros(q.shape[0])
    for i in range(q.shape[0]):
        ok = ~np.isnan(f[i, :, 0])
        counts = np.bincount(geometry.tile_index(f[i, ok]), minlength=geometry.ROWS * geometry.COLS)
        p = counts[counts > 0] / counts.sum()
        out[i] = float(-(p * np.log2(p)).sum())
    return out


def on_crowd(segments: np.ndarray, region_tiles: int = REGION_TILES) -> np.ndarray:
    """(viewers, segments, tiles) -> (viewers,): share of each viewer's window on the
    `region_tiles` tiles most watched by the OTHER viewers, averaged over segments."""
    present = ~np.isnan(segments[..., 0])
    filled = np.where(present[..., None], segments, 0)
    total, count = filled.sum(axis=0), present.sum(axis=0)
    out = np.zeros(segments.shape[0])
    for i in range(segments.shape[0]):
        others = (total - filled[i]) / np.maximum(count - present[i], 1)[:, None]
        cov = metrics.coverage(predict.choose_tiles(others, region_tiles), segments[i])
        out[i] = np.nanmean(cov)
    return out


def video_features(cache: Path, video: str) -> pd.DataFrame:
    """One row per viewer for one video, from the parsed cache."""
    z = np.load(Path(cache) / f"{video}.npz")
    hz = int(z["hz"])
    segments = predict.segment_weights(z["weights"], hz)
    return pd.DataFrame({
        "video": video,
        "viewer": z["viewers"],
        "head_speed": head_speed(z["q"], hz),
        "exploration": exploration(z["q"]),
        "on_crowd": on_crowd(segments),
    })


def standardise(features: pd.DataFrame) -> pd.DataFrame:
    """z-score each feature among the viewers of the same video."""
    out = features.copy()
    for name in FEATURES:
        g = out.groupby("video")[name]
        out[name] = (out[name] - g.transform("mean")) / g.transform("std")
    return out


def style_for(z_features: pd.DataFrame, test_video: str, allowed_videos=None) -> pd.DataFrame:
    """Each viewer's style for one test video: mean z-score over the training videos.

    The test video is always left out. `allowed_videos` can narrow the training
    videos further, for example to those from the same experiment."""
    train = z_features[z_features["video"] != test_video]
    if allowed_videos is not None:
        train = train[train["video"].isin([v for v in allowed_videos if v != test_video])]
    return train.groupby("viewer")[list(FEATURES)].mean().sort_index()


def mixed_group(pool: np.ndarray, k: int, rng: np.random.Generator, style: np.ndarray) -> np.ndarray:
    """One viewer per style cluster: the one nearest each cluster's centre.
    `style` is (all viewers, features), indexed by the same row numbers as `pool`."""
    if k >= len(pool):
        return np.sort(pool)
    x = style[pool]
    km = KMeans(n_clusters=k, n_init=5, random_state=int(rng.integers(0, 2**31 - 1))).fit(x)
    chosen = []
    for c in range(k):
        members = np.flatnonzero(km.labels_ == c)
        dist = np.linalg.norm(x[members] - km.cluster_centers_[c], axis=1)
        chosen.append(pool[members[np.argmin(dist)]])
    return np.sort(np.array(chosen))


def typical_group(pool: np.ndarray, k: int, rng: np.random.Generator, style: np.ndarray) -> np.ndarray:
    """The k pool viewers who stay on the crowd most (highest on_crowd z-score)."""
    order = np.argsort(-style[pool, FEATURES.index("on_crowd")], kind="stable")
    return np.sort(pool[order[:k]])


def split_half_reliability(z_features: pd.DataFrame, videos_a, videos_b) -> dict:
    """Correlation across viewers between a feature's mean on two disjoint sets of videos.
    High means the feature is a trait of the person, not of the moment."""
    a = z_features[z_features["video"].isin(videos_a)].groupby("viewer")[list(FEATURES)].mean()
    b = z_features[z_features["video"].isin(videos_b)].groupby("viewer")[list(FEATURES)].mean()
    return {name: float(a[name].corr(b[name])) for name in FEATURES}
