"""A tiny synthetic dataset in the real folder layout. No real data is needed."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HEADER = "Timestamp,PlaybackTime,UnitQuaternion.x,UnitQuaternion.y,UnitQuaternion.z,UnitQuaternion.w,HmdPosition.x,HmdPosition.y,HmdPosition.z"


def yaw_quaternion(yaw_deg):
    """Unit quaternion for a turn about the vertical axis (Unity: y up)."""
    half = np.radians(np.asarray(yaw_deg, float)) / 2
    zero = np.zeros_like(half)
    return np.stack([zero, np.sin(half), zero, np.cos(half)], axis=-1)


def write_session(path: Path, start: pd.Timestamp, seconds: float, yaw_deg=0.0, height=1.2, hz=90, stale_rows=0):
    """Write one session file. `yaw_deg` may be a number or a function of playback time."""
    n = int(seconds * hz)
    t = np.arange(n) / hz
    yaw = yaw_deg(t) if callable(yaw_deg) else np.full(n, float(yaw_deg))
    q = yaw_quaternion(yaw)
    stamps = start + pd.to_timedelta(t, unit="s")
    lines = [HEADER]
    for i in range(stale_rows):  # leftover playback time from the previous video
        lines.append(f"{(start - pd.Timedelta(11 * (stale_rows - i), unit="ms")).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]},"
                     f"{3.2 + i * 0.011:.3f},0.000,0.000,0.000,1.000,0.000,{height:.3f},0.000")
    for i in range(n):
        lines.append(f"{stamps[i].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]},{t[i]:.3f},"
                     f"{q[i, 0]:.3f},{q[i, 1]:.3f},{q[i, 2]:.3f},{q[i, 3]:.3f},0.000,{height:.3f},0.000")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_dataset(root: Path, viewers=(1, 2, 3, 4), seconds=4.0, exp2_order=None, heights=None, seed=0):
    """Each viewer sits once per experiment and watches nine short videos in order.
    Experiment 1 is recorded in folder order. Experiment 2 in `exp2_order`."""
    rng = np.random.default_rng(seed)
    heights = heights or {v: 1.0 + 0.05 * v for v in viewers}
    orders = {1: list(viewers), 2: list(exp2_order or reversed(viewers))}
    days = {1: pd.Timestamp("2016-11-17 02:00:00"), 2: pd.Timestamp("2016-11-29 01:00:00")}
    for e in (1, 2):
        for slot, viewer in enumerate(orders[e]):
            start = days[e] + pd.Timedelta(3600 * slot, unit="s")
            for i in range(9):
                write_session(root / f"Experiment_{e}" / str(viewer) / f"video_{i}.csv",
                              start + pd.Timedelta(i * (seconds + 20), unit="s"), seconds,
                              yaw_deg=float(rng.uniform(-60, 60)),
                              height=heights[viewer] + float(rng.normal(0, 0.005)))
        meta = ["VideoNo,VideoResolution,VideoDuration,FrameRate,FrameCount,Content,Category,Bitrate,VideoLink,DropboxLink"]
        meta += [f"{i + 1},2560*1440,0:04,30,120,Clip {e}-{i + 1},Sport,5000,https://example.org,https://example.org" for i in range(9)]
        (root / f"Experiment_{e}" / "videoMeta.csv").write_text("\n".join(meta) + "\n", encoding="utf-8")
    demo = ["No.,Gender,Age"] + [f"{v},Female,20~25" for v in viewers]
    (root / "userDemo.csv").write_text("\n".join(demo) + "\n", encoding="utf-8")
    return root


@pytest.fixture
def tiny_root(tmp_path):
    return make_dataset(tmp_path / "Formated_Data")


def make_cache(cache: Path, videos, n_viewers=12, seconds=14, hz=10, seed=0, styles=None):
    """Write processed-video files like src/parse.py does, without raw data.

    Each viewer has a fixed style across videos:
      "still"    stares at the video's main spot
      "follow"   tracks a spot that drifts slowly
      "explore"  sweeps steadily round the whole frame
    By default the first half are "still", then a quarter each of the others."""
    from src import geometry

    rng = np.random.default_rng(seed)
    if styles is None:
        styles = ["still"] * (n_viewers // 2) + ["follow"] * (n_viewers // 4)
        styles += ["explore"] * (n_viewers - len(styles))
    t = np.arange(seconds * hz) / hz
    cache.mkdir(parents=True, exist_ok=True)
    for video in videos:
        spot = rng.uniform(-180, 180)
        drift = spot + 25 * np.sin(2 * np.pi * t / seconds)
        yaws = []
        for style in styles:
            if style == "still":
                yaws.append(np.full_like(t, spot + rng.normal(0, 3)))
            elif style == "follow":
                yaws.append(drift + rng.normal(0, 3))
            else:
                yaws.append(rng.uniform(-180, 180) + rng.choice([-1, 1]) * rng.uniform(50, 70) * t)
        q = np.stack([yaw_quaternion(y) for y in yaws])
        np.savez_compressed(cache / f"{video}.npz", q=q, weights=geometry.tile_weights(q),
                            viewers=np.arange(1, n_viewers + 1), hz=hz)
    return styles
