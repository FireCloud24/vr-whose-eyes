"""Where the raw files live and how to read them.

Layout after scripts/download.py:

    data/raw/Formated_Data/userDemo.csv
    data/raw/Formated_Data/Experiment_{1,2}/videoMeta.csv
    data/raw/Formated_Data/Experiment_{1,2}/{viewer 1..48}/video_{0..8}.csv

A "session" is one viewer watching one video. I name a video by experiment and
play order, for example "1-3" for the third video of experiment 1, which is the
same naming the authors use for their video files.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_ROOT = Path("data/raw/Formated_Data")
EXPERIMENTS = (1, 2)
VIEWERS = tuple(range(1, 49))
VIDEOS_PER_EXPERIMENT = 9
COLUMNS = {
    "Timestamp": "timestamp",
    "PlaybackTime": "t",
    "UnitQuaternion.x": "qx",
    "UnitQuaternion.y": "qy",
    "UnitQuaternion.z": "qz",
    "UnitQuaternion.w": "qw",
    "HmdPosition.x": "px",
    "HmdPosition.y": "py",
    "HmdPosition.z": "pz",
}


def video_id(experiment: int, index: int) -> str:
    """index is the 0-based number in the file name; the id is 1-based like the paper."""
    return f"{experiment}-{index + 1}"


def all_videos() -> list[str]:
    return [video_id(e, i) for e in EXPERIMENTS for i in range(VIDEOS_PER_EXPERIMENT)]


def session_path(root: Path, video: str, viewer: int) -> Path:
    experiment, number = video.split("-")
    return Path(root) / f"Experiment_{experiment}" / str(viewer) / f"video_{int(number) - 1}.csv"


def read_raw(root: Path, video: str, viewer: int) -> pd.DataFrame:
    """One session exactly as recorded, with short column names and parsed timestamps."""
    df = pd.read_csv(session_path(root, video, viewer)).rename(columns=COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df[list(COLUMNS.values())]


def read_video_meta(root: Path) -> pd.DataFrame:
    """Both experiments' videoMeta.csv in one table, keyed by video id."""
    frames = []
    for e in EXPERIMENTS:
        m = pd.read_csv(Path(root) / f"Experiment_{e}" / "videoMeta.csv")
        m.insert(0, "video", [f"{e}-{n}" for n in m["VideoNo"]])
        m.insert(1, "experiment", e)
        frames.append(m)
    meta = pd.concat(frames, ignore_index=True)
    minutes = meta["VideoDuration"].str.split(":", expand=True).astype(int)
    meta["duration_s"] = minutes[0] * 60 + minutes[1]
    return meta


def read_viewers(root: Path) -> pd.DataFrame:
    return pd.read_csv(Path(root) / "userDemo.csv").rename(columns={"No.": "viewer"})
