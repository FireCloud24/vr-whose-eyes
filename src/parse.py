"""Turn raw session files into one tidy array per video.

What the raw files look like (checked before writing this):
- about 90 rows a second, each with the video's playback time `t`;
- the first rows of a file can still carry the previous video's playback time,
  after which `t` drops to zero;
- `t` jitters backwards by a few milliseconds now and then;
- after the video ends, rows keep coming with `t` frozen at the last value.

So I put every viewer on the same clock, the video's own playback time, sampled
`HZ` times a second. For each tick I take the recorded row nearest in playback
time. A tick with no row within `MAX_GAP_S` is marked missing (NaN).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src import data, geometry

HZ = 10
MAX_GAP_S = 0.25
QUATERNION = ["qx", "qy", "qz", "qw"]
PROCESSED = Path("data/processed")


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the rows where the video was really playing, with `t` strictly increasing."""
    t = df["t"].to_numpy()
    drops = np.flatnonzero(np.diff(t) < -0.5)
    if len(drops):  # leftover rows from the previous video
        df = df.iloc[drops[-1] + 1:]
        t = df["t"].to_numpy()
    running_max = np.maximum.accumulate(t)
    keep = np.ones(len(t), dtype=bool)
    keep[1:] = t[1:] > running_max[:-1]  # drops backward jitter, repeats and the frozen tail
    return df.iloc[keep].reset_index(drop=True)


def resample(df: pd.DataFrame, n_ticks: int, hz: int = HZ, max_gap: float = MAX_GAP_S) -> np.ndarray:
    """Cleaned session -> (n_ticks, 4) unit quaternions at ticks 0, 1/hz, 2/hz, ..."""
    t = df["t"].to_numpy()
    q = df[QUATERNION].to_numpy(float)
    ticks = np.arange(n_ticks) / hz
    right = np.clip(np.searchsorted(t, ticks), 0, len(t) - 1)
    left = np.clip(right - 1, 0, len(t) - 1)
    nearest = np.where(np.abs(t[left] - ticks) <= np.abs(t[right] - ticks), left, right)
    out = geometry.normalise(q[nearest])
    out[np.abs(t[nearest] - ticks) > max_gap] = np.nan
    return out


def load_video(root: Path, video: str, viewers=data.VIEWERS, hz: int = HZ) -> dict:
    """All viewers of one video on a shared clock.

    Returns {"q": (viewers, ticks, 4), "viewers": [...], "hz": hz}. The length is
    the shortest viewer's last playback time, so every viewer covers every tick."""
    sessions = [clean(data.read_raw(root, video, v)) for v in viewers]
    n_ticks = int(np.floor(min(s["t"].iloc[-1] for s in sessions) * hz))
    q = np.stack([resample(s, n_ticks, hz) for s in sessions])
    return {"q": q, "viewers": np.array(viewers), "hz": hz}


def cached_video(root: Path, video: str, cache: Path = PROCESSED, viewers=data.VIEWERS) -> dict:
    """load_video with an on-disk cache, plus tile weights at 6 x 12."""
    cache = Path(cache)
    path = cache / f"{video}.npz"
    if path.exists():
        z = np.load(path)
        return {k: z[k] for k in z.files}
    v = load_video(root, video, viewers)
    v["weights"] = geometry.tile_weights(v["q"])
    cache.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **v)
    return v
