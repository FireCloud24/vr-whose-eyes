"""The experiment loop shared by every comparison in this project.

One trial, for one test video:

1. Split the 48 viewers at random into 16 test viewers and a pool of 32.
   The test viewers stand for people who have not watched yet. Nothing about
   them is used to pick a group.
2. For each group size k and each way of picking ("arm"), pick k viewers from
   the pool. Their traces on the test video are the crowd.
3. For every one-second segment, fetch the top `budget` tiles and score each
   test viewer's coverage.

The same split is used for every arm and every k, so differences between arms
are paired. At k = 32 the group is the whole pool, so all arms coincide there.

The first five segments of each video are left out everywhere, so that all
horizons (1, 2 and 5 seconds) are scored on exactly the same segments.
"""
from __future__ import annotations

import zlib
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from src import metrics, predict

N_TEST = 16
BUDGET = 16
KS = (1, 2, 4, 8, 16, 32)
SKIP = max(predict.HORIZONS)

Picker = Callable[[np.ndarray, int, np.random.Generator], np.ndarray]


def load_video(cache: Path, video: str) -> dict:
    """Segment-level arrays for one video, from the cache written in the parsing step."""
    z = np.load(Path(cache) / f"{video}.npz")
    hz = int(z["hz"])
    return {
        "video": video,
        "segments": predict.segment_weights(z["weights"], hz),
        "instant": predict.instant_weights(z["weights"], hz),
        "viewers": z["viewers"],
    }


def split_viewers(n_viewers: int, n_test: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Random (pool, test) row numbers, each sorted."""
    order = rng.permutation(n_viewers)
    return np.sort(order[n_test:]), np.sort(order[:n_test])


def random_group(pool: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    return np.sort(rng.choice(pool, size=k, replace=False))


def own_motion_coverage(vd: dict, budget: int = BUDGET, horizons=predict.HORIZONS) -> dict:
    """{horizon: (viewers, segments - SKIP) coverage} when each viewer is served from
    their own position `horizon` seconds earlier. No other viewer is involved."""
    actual = vd["segments"][:, SKIP:]
    out = {}
    for h in horizons:
        chosen = predict.choose_tiles(predict.own_motion_scores(vd["instant"], h), budget)[:, SKIP:]
        out[h] = metrics.coverage(chosen, actual)
    return out


def group_coverage(vd: dict, group: np.ndarray, test: np.ndarray, budget: int = BUDGET,
                   own_weights: dict | None = None) -> dict:
    """Coverage of each test viewer when tiles come from this group.

    Returns {"crowd": (test viewers, segments - SKIP)} plus {"blend_h": ...} for
    each horizon h in `own_weights` ({horizon: weight on the viewer's own motion})."""
    crowd = predict.crowd_scores(vd["segments"], group)
    actual = vd["segments"][test][:, SKIP:]
    out = {"crowd": metrics.coverage(predict.choose_tiles(crowd, budget)[None, SKIP:], actual)}
    for h, weight in (own_weights or {}).items():
        own = predict.own_motion_scores(vd["instant"][test], h)[:, SKIP:]
        chosen = predict.choose_tiles(predict.blend_scores(own, crowd[SKIP:], weight), budget)
        out[f"blend_{h}"] = metrics.coverage(chosen, actual)
    return out


def score(cov: np.ndarray) -> dict:
    """(test viewers, segments) coverage -> the four numbers reported per trial."""
    per_viewer = metrics.mean_coverage(cov, axis=1)
    poor = metrics.poor_seconds_per_minute(cov, axis=1)
    return {
        "coverage": float(per_viewer.mean()),
        "coverage_worst10": metrics.tail_mean(per_viewer, worst="low"),
        "poor_s_per_min": float(poor.mean()),
        "poor_s_per_min_worst10": metrics.tail_mean(poor, worst="high"),
    }


def run_video(vd: dict, arms: dict[str, Picker], ks=KS, n_trials: int = 200, seed: int = 0,
              budget: int = BUDGET, own_weights: dict | None = None, n_test: int = N_TEST) -> pd.DataFrame:
    """All trials for one test video. One row per trial, arm, k and method.

    `arms` maps a name to a function (pool, k, rng) -> group. `own_weights` maps
    k -> {horizon: weight}; leave it out to score the crowd alone. Own-motion
    rows (arm "none", k 0) are scored on the same test viewers in every trial.

    Random numbers: the splits depend only on `seed`, and each arm's draws depend
    only on (seed, arm name, k, trial). So adding an arm or a group size never
    changes the numbers of the others, and two scripts with the same seed see
    the same splits and the same random groups."""
    n_viewers = vd["segments"].shape[0]
    own = own_motion_coverage(vd, budget)
    split_rng = np.random.default_rng([seed, 0])
    rows = []
    for trial in range(n_trials):
        pool, test = split_viewers(n_viewers, n_test, split_rng)
        for h, cov in own.items():
            rows.append({"trial": trial, "arm": "none", "k": 0, "method": f"own_{h}", **score(cov[test])})
        for k in ks:
            for arm, pick in arms.items():
                group = pick(pool, k, np.random.default_rng([seed, 1, zlib.crc32(arm.encode()), k, trial]))
                covs = group_coverage(vd, group, test, budget, (own_weights or {}).get(k))
                for method, cov in covs.items():
                    rows.append({"trial": trial, "arm": arm, "k": k, "method": method, **score(cov)})
    out = pd.DataFrame(rows)
    out.insert(0, "video", vd["video"])
    return out


def run_parallel(fn, tasks: list[tuple], jobs: int = 1) -> list:
    """fn(*task) for every task, in order. With jobs > 1 the tasks run in separate
    processes. Results do not depend on `jobs`, because each task carries its own seed."""
    if jobs <= 1 or len(tasks) <= 1:
        return [fn(*t) for t in tasks]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(fn, *t) for t in tasks]
        return [f.result() for f in futures]


METRICS = ("coverage", "coverage_worst10", "poor_s_per_min", "poor_s_per_min_worst10")


def per_video(trials: pd.DataFrame) -> pd.DataFrame:
    """Average the trials: one row per video, arm, k and method."""
    return trials.groupby(["video", "arm", "k", "method"], as_index=False)[list(METRICS)].mean()


def bootstrap_mean(values, n_boot: int = 10000, seed: int = 0, level: float = 0.95) -> tuple[float, float, float]:
    """Mean of per-video values with a percentile bootstrap interval over videos."""
    v = np.asarray(values, float)
    rng = np.random.default_rng(seed)
    means = v[rng.integers(0, len(v), size=(n_boot, len(v)))].mean(axis=1)
    lo, hi = np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(v.mean()), float(lo), float(hi)


def across_videos(table: pd.DataFrame, n_boot: int = 10000, seed: int = 0) -> pd.DataFrame:
    """Per-video table -> one row per arm, k and method with the mean over videos and
    a 95% bootstrap interval. Videos are the unit: each one is a separate held-out test."""
    rows = []
    for (arm, k, method), g in table.groupby(["arm", "k", "method"]):
        row = {"arm": arm, "k": k, "method": method, "videos": len(g)}
        for m in METRICS:
            mean, lo, hi = bootstrap_mean(g[m], n_boot, seed)
            row.update({m: mean, f"{m}_lo": lo, f"{m}_hi": hi})
        rows.append(row)
    return pd.DataFrame(rows)


def paired_differences(table: pd.DataFrame, baseline: tuple = ("random", None), n_boot: int = 10000, seed: int = 0) -> pd.DataFrame:
    """Per-video table -> differences from a baseline, video by video.

    baseline = (arm, k). With k None each row is compared with the baseline arm at
    the same k. With a number, every row is compared with the baseline arm at that
    k. One output row per arm, k, method and metric: the mean difference over
    videos, a 95% bootstrap interval over videos, and in how many videos the
    difference was above zero."""
    base_arm, base_k = baseline
    base = table[table["arm"] == base_arm]
    if base_k is not None:
        base = base[base["k"] == base_k]
    rows = []
    for (arm, k, method), g in table[table["arm"] != "none"].groupby(["arm", "k", "method"]):
        b = base[(base["method"] == method) & ((base["k"] == k) if base_k is None else True)]
        merged = g.merge(b, on="video", suffixes=("", "_base"))
        if merged.empty or (arm == base_arm and (base_k is None or k == base_k)):
            continue
        for m in METRICS:
            diff = (merged[m] - merged[f"{m}_base"]).to_numpy()
            mean, lo, hi = bootstrap_mean(diff, n_boot, seed)
            rows.append({"arm": arm, "k": k, "method": method, "metric": m, "baseline": f"{base_arm} k={'same' if base_k is None else base_k}",
                         "difference": mean, "lo": lo, "hi": hi, "videos": len(diff), "videos_above_zero": int((diff > 0).sum())})
    return pd.DataFrame(rows)
