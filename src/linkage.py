"""Does a viewer folder mean the same person in every video?

The whole project needs this. Viewing style is measured on some videos and used
on another, so folder "17" has to be one person throughout. The files carry no
name or device id, so I check what the recordings themselves can show:

- within an experiment, a folder's nine videos should be one sitting: recorded
  one after another, in play order, in well under two hours;
- there was one headset, so two folders should never be recorded at the same time;
- across the two experiments, the folder numbers should not just be arrival
  order in both (that would suggest numbers were handed out afresh);
- headset height while seated is a physical trace of the person. It should agree
  between the two halves of a sitting, and somewhat between the experiments.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src import data


def session_table(root: Path, viewers=data.VIEWERS, videos=None) -> pd.DataFrame:
    """One row per session: when it was recorded, how many rows, median headset height."""
    rows = []
    for video in videos or data.all_videos():
        for viewer in viewers:
            df = data.read_raw(root, video, viewer)
            rows.append({
                "experiment": int(video.split("-")[0]),
                "video": video,
                "viewer": viewer,
                "start": df["timestamp"].iloc[0],
                "end": df["timestamp"].iloc[-1],
                "rows": len(df),
                "height_m": float(df["py"].median()),
            })
    return pd.DataFrame(rows)


def sittings(sessions: pd.DataFrame) -> pd.DataFrame:
    """One row per experiment and viewer: was it a single sitting in play order?"""
    out = []
    for (experiment, viewer), g in sessions.groupby(["experiment", "viewer"]):
        by_number = g.assign(number=g["video"].str.split("-").str[1].astype(int)).sort_values("number")
        in_order = bool(by_number["start"].is_monotonic_increasing and by_number["start"].is_unique)
        span = (g["end"].max() - g["start"].min()).total_seconds() / 60
        out.append({
            "experiment": experiment,
            "viewer": viewer,
            "videos": len(g),
            "first_start": g["start"].min(),
            "span_minutes": span,
            "in_play_order": in_order,
            "one_sitting": bool(in_order and span < 120 and len(g) == data.VIDEOS_PER_EXPERIMENT),
        })
    return pd.DataFrame(out)


def overlapping_pairs(sessions: pd.DataFrame) -> int:
    """How many pairs of sessions from different viewers overlap in time."""
    s = sessions.sort_values("start").reset_index(drop=True)
    start, end, viewer = s["start"].to_numpy(), s["end"].to_numpy(), s["viewer"].to_numpy()
    count = 0
    for i in range(len(s)):
        j = i + 1
        while j < len(s) and start[j] < end[i]:
            count += int(viewer[j] != viewer[i])
            j += 1
    return count


def rank_correlation(a, b) -> float:
    """Spearman correlation: Pearson correlation of the ranks."""
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def arrival_order_correlation(sit: pd.DataFrame, experiment: int) -> float:
    """Rank correlation between folder number and when that folder was recorded."""
    g = sit[sit["experiment"] == experiment]
    return rank_correlation(g["viewer"], g["first_start"].astype("int64"))


def permutation_p(x, y, n_perm: int = 10000, seed: int = 0) -> float:
    """One-sided p-value for corr(x, y) > 0, shuffling which y goes with which x."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rng = np.random.default_rng(seed)
    observed = np.corrcoef(x, y)[0, 1]
    hits = sum(np.corrcoef(x, rng.permutation(y))[0, 1] >= observed for _ in range(n_perm))
    return (hits + 1) / (n_perm + 1)


def height_agreement(sessions: pd.DataFrame, n_perm: int = 10000, seed: int = 0) -> dict:
    """Correlation of median headset height per viewer:
    - between odd and even videos of the same sitting (same person for sure, if
      a folder is one sitting), as a reference for how repeatable height is;
    - between experiment 1 and experiment 2, which were recorded days apart."""
    number = sessions["video"].str.split("-").str[1].astype(int)
    s = sessions.assign(half=np.where(number % 2 == 1, "odd", "even"))
    result = {}
    for experiment, g in s.groupby("experiment"):
        halves = g.groupby(["viewer", "half"])["height_m"].median().unstack("half")
        result[f"within_experiment_{experiment}_r"] = float(halves["odd"].corr(halves["even"]))
    per = s.groupby(["viewer", "experiment"])["height_m"].median().unstack("experiment")
    result["across_experiments_r"] = float(per[1].corr(per[2]))
    result["across_experiments_p"] = float(permutation_p(per[1], per[2], n_perm, seed))
    result["viewers"] = int(len(per))
    return result
