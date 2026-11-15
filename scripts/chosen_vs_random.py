"""Viewing styles, then chosen groups against random groups of the same size.

    python scripts/chosen_vs_random.py

Order matters here. The script first measures each viewer's style and checks
that style is a stable trait (results/style_check.md). Only if it is does it go
on to any outcome. If no feature is stable, it stops with exit status 2.

Then, for every held-out video, the same trials as the baselines are run with
three ways of picking k viewers from the pool:

  random   any k
  mixed    one viewer from each of k style clusters
  typical  the k viewers who stay on the crowd most (a control)

Style for a test video comes only from the other videos. A second run uses only
other videos from the same experiment, because the link between the two
experiments' viewer numbers rests partly on trust (results/id_linkage.md). That
second run scores the crowd alone, without the blend, to keep it quick.

Writes:
  results/style_features.csv                 one row per viewer and video
  results/style_check.md                     stability of the features, before any outcome
  results/chosen_vs_random_per_video.csv     one row per video, arm, k and method
  results/chosen_vs_random.csv               mean over videos with intervals
  results/chosen_vs_random_diff.csv          paired differences from random at the same k
  results/chosen_vs_random_same_experiment_diff.csv   the same, with same-experiment styles
  results/chosen_vs_random.md / .png         the table and the figure
"""
from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import data, evaluate, metrics, parse, predict, styles

STABLE_ENOUGH = 0.3  # split-half correlation below this means "not a trait"
ARMS = ("random", "mixed", "typical")
ARM_LABEL = {"random": "random", "mixed": "mixed (one per style cluster)", "typical": "typical (most on the crowd)"}
ARM_COLOUR = {"random": "black", "mixed": "#d95f02", "typical": "#1b9e77"}


def experiment_videos(e: int) -> list[str]:
    return [v for v in data.all_videos() if v.startswith(f"{e}-")]


def style_check(z: pd.DataFrame) -> dict:
    """Split-half correlations of each feature across viewers, for several ways of
    splitting the videos. All of this uses viewing behaviour only, no outcome."""
    videos = sorted(z["video"].unique())
    e1, e2 = [v for v in videos if v.startswith("1-")], [v for v in videos if v.startswith("2-")]
    return {
        "odd vs even videos, all": styles.split_half_reliability(z, videos[::2], videos[1::2]),
        "odd vs even videos, experiment 1": styles.split_half_reliability(z, e1[::2], e1[1::2]),
        "odd vs even videos, experiment 2": styles.split_half_reliability(z, e2[::2], e2[1::2]),
        "experiment 1 vs experiment 2": styles.split_half_reliability(z, e1, e2),
    }


def is_stable(check: dict) -> bool:
    return max(check["odd vs even videos, all"].values()) >= STABLE_ENOUGH


def render_style_check(features: pd.DataFrame, z: pd.DataFrame, check: dict) -> str:
    raw = features.groupby("viewer")[list(styles.FEATURES)].mean()
    mean_z = z.groupby("viewer")[list(styles.FEATURES)].mean()
    corr = mean_z.corr()
    lines = [
        "# Is viewing style a stable trait?",
        "",
        "Written by `scripts/chosen_vs_random.py` before any outcome is computed. Each feature is a",
        "z-score among the 48 viewers of a video. The table gives the correlation across viewers",
        "between a feature's average on one set of videos and on a disjoint set. Near 1 means the",
        "feature belongs to the person. Near 0 means it belongs to the moment.",
        "",
        "| Split | Head speed | Exploration | On the crowd |",
        "|---|---|---|---|",
    ]
    for name, r in check.items():
        lines.append(f"| {name} | {r['head_speed']:.2f} | {r['exploration']:.2f} | {r['on_crowd']:.2f} |")
    lines += [
        "",
        "The last row doubles as a check on viewer numbers. If folder 17 were a different person",
        "in the two experiments, these correlations would be near zero.",
        "",
        "## Spread between viewers (raw values, averaged over the 18 videos)",
        "",
        "| Feature | Lowest viewer | Median | Highest viewer |",
        "|---|---|---|---|",
        f"| Head speed (degrees per second) | {raw['head_speed'].min():.1f} | {raw['head_speed'].median():.1f} | {raw['head_speed'].max():.1f} |",
        f"| Exploration (bits) | {raw['exploration'].min():.2f} | {raw['exploration'].median():.2f} | {raw['exploration'].max():.2f} |",
        f"| On the crowd (share of window) | {raw['on_crowd'].min():.2f} | {raw['on_crowd'].median():.2f} | {raw['on_crowd'].max():.2f} |",
        "",
        "## How the features relate (correlation of viewers' average z-scores)",
        "",
        "| | Head speed | Exploration | On the crowd |",
        "|---|---|---|---|",
    ]
    for a in styles.FEATURES:
        lines.append(f"| {a} | " + " | ".join(f"{corr.loc[a, b]:.2f}" for b in styles.FEATURES) + " |")
    lines += ["", ("At least one feature is stable enough to group viewers by, so the comparison goes ahead."
                   if is_stable(check) else
                   "No feature is stable. Grouping viewers by style has nothing to work with, so the script stops here."), ""]
    return "\n".join(lines)


def evaluate_one(vd: dict, style: np.ndarray, ks, n_trials: int, seed: int, budget: int, weights: dict, n_test: int) -> pd.DataFrame:
    arms = {
        "random": evaluate.random_group,
        "mixed": functools.partial(styles.mixed_group, style=style),
        "typical": functools.partial(styles.typical_group, style=style),
    }
    return evaluate.run_video(vd, arms, ks, n_trials, seed, budget, weights, n_test)


def run_all(videos: list[dict], z: pd.DataFrame, weights: pd.DataFrame, args, same_experiment: bool) -> pd.DataFrame:
    tasks = []
    for i, vd in enumerate(videos):
        allowed = experiment_videos(int(vd["video"][0])) if same_experiment else None
        style = styles.style_for(z, vd["video"], allowed).loc[vd["viewers"]].to_numpy()
        blend = {} if same_experiment else weights_for(weights, vd["video"])  # the check run scores the crowd alone
        tasks.append((vd, style, args.ks, args.trials, args.seed + i, args.budget, blend, args.n_test))
    return evaluate.per_video(pd.concat(evaluate.run_parallel(evaluate_one, tasks, args.jobs)))


def weights_for(used: pd.DataFrame, video: str) -> dict:
    out: dict = {}
    for r in used[used["video"] == video].itertuples():
        out.setdefault(int(r.k), {})[int(r.horizon)] = float(r.own_weight)
    return out


def fmt_diff(row, scale: float = 100, digits: int = 1) -> str:
    return (f"{scale * row['difference']:+.{digits}f} ({scale * row['lo']:+.{digits}f} to {scale * row['hi']:+.{digits}f}), "
            f"{row['videos_above_zero']}/{row['videos']}")


def diff_table(diff: pd.DataFrame, method: str, ks) -> list[str]:
    d = diff[diff["method"] == method].set_index(["arm", "k", "metric"])
    lines = ["| k | Arm | Coverage, average viewer | Coverage, worst 10% | Poor seconds per minute, worst 10% |", "|---|---|---|---|---|"]
    for k in ks:
        for arm in ARMS[1:]:
            if (arm, k, "coverage") not in d.index:
                continue
            lines.append(f"| {k} | {arm} | {fmt_diff(d.loc[(arm, k, 'coverage')])} | {fmt_diff(d.loc[(arm, k, 'coverage_worst10')])} | "
                         f"{fmt_diff(d.loc[(arm, k, 'poor_s_per_min_worst10')], 1)} |")
    return lines


def render(summary: pd.DataFrame, diff: pd.DataFrame, diff_same: pd.DataFrame, args) -> str:
    s = summary.set_index(["arm", "k", "method"])
    ks = [k for k in args.ks]
    lines = [
        "# Chosen groups against random groups of the same size",
        "",
        f"Written by `scripts/chosen_vs_random.py`. Budget {args.budget} of 72 tiles, {args.trials} trials per video, 18 held-out",
        "videos. In each trial the three arms pick k viewers from the same pool of 32 and are scored on",
        "the same 16 test viewers. Style comes from the other 17 videos.",
        "",
        "## Levels: crowd only, coverage %",
        "",
        "| k | " + " | ".join(f"{a}, average | {a}, worst 10%" for a in ARMS) + " |",
        "|---|" + "---|---|" * len(ARMS),
    ]
    for k in ks:
        cells = []
        for a in ARMS:
            r = s.loc[(a, k, "crowd")]
            cells += [f"{100 * r['coverage']:.1f}", f"{100 * r['coverage_worst10']:.1f}"]
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## Differences from random at the same k",
        "",
        "Each cell is the mean difference over videos, its 95% bootstrap interval over videos, and the",
        "number of videos in which the arm beat random. Coverage is in percentage points, where above",
        "zero is better. Poor seconds are per minute, where below zero is better. At k = 32 the group is",
        "the whole pool, so every arm is the same and the row is left out.",
        "",
        "### Crowd only",
        "",
        *diff_table(diff, "crowd", ks),
        "",
        "### Blend of own motion and crowd, 2 seconds ahead",
        "",
        *diff_table(diff, "blend_2", ks),
        "",
        "### Blend, 5 seconds ahead",
        "",
        *diff_table(diff, "blend_5", ks),
        "",
        "## Same comparison with style taken from the same experiment only (crowd only)",
        "",
        "Here a viewer's style for a test video uses just the other eight videos of that experiment,",
        "so nothing depends on viewer numbers matching across the two experiments.",
        "",
        *diff_table(diff_same, "crowd", ks),
        "",
    ]
    return "\n".join(lines)


def figure(summary: pd.DataFrame, diff: pd.DataFrame, path: Path, args):
    s = summary.set_index(["arm", "k", "method"])
    d = diff[diff["method"] == "crowd"].set_index(["arm", "k", "metric"])
    ks = list(args.ks)
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.6))
    panels = (("coverage", "average viewer"), ("coverage_worst10", "worst-served 10% of viewers"))
    for col, (metric, who) in enumerate(panels):
        ax = axes[0, col]
        for arm in ARMS:
            ax.plot(ks, [100 * s.loc[(arm, k, "crowd"), metric] for k in ks], "o-", color=ARM_COLOUR[arm], label=ARM_LABEL[arm], ms=4)
        ax.set_ylabel(f"coverage, {who} (%)")
        ax.set_title(f"Coverage for the {who}", fontsize=9)
        ax = axes[1, col]
        ax.axhline(0, color="black", lw=0.8)
        for offset, arm in ((-0.04, "mixed"), (0.04, "typical")):
            kk = [k for k in ks if (arm, k, metric) in d.index]
            mean = np.array([100 * d.loc[(arm, k, metric), "difference"] for k in kk])
            lo = np.array([100 * d.loc[(arm, k, metric), "lo"] for k in kk])
            hi = np.array([100 * d.loc[(arm, k, metric), "hi"] for k in kk])
            x = np.array(kk) * 2 ** offset
            ax.errorbar(x, mean, yerr=[mean - lo, hi - mean], fmt="o", color=ARM_COLOUR[arm], capsize=3, ms=4, label=f"{arm} minus random")
        ax.set_ylabel("difference from random (points)")
        ax.set_title(f"Difference from a random group of the same size, {who}", fontsize=9)
    for ax in axes.ravel():
        ax.set_xscale("log", base=2)
        ax.set_xticks(ks)
        ax.set_xticklabels([str(k) for k in ks])
        ax.set_xlabel("earlier viewers in the group (k)")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7)
    fig.suptitle(f"Chosen against random groups: crowd heatmap only, {args.budget} of 72 tiles, 18 held-out videos\n"
                 "(bars: 95% bootstrap interval over videos)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", default=str(parse.PROCESSED))
    p.add_argument("--out", default="results")
    p.add_argument("--trials", type=int, default=200)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ks", type=int, nargs="*", default=list(evaluate.KS))
    p.add_argument("--n-test", type=int, default=evaluate.N_TEST)
    p.add_argument("--budget", type=int, default=evaluate.BUDGET)
    p.add_argument("--jobs", type=int, default=6)
    p.add_argument("--check-only", action="store_true", help="stop after the style check")
    args = p.parse_args(argv)
    out, cache = Path(args.out), Path(args.cache)
    out.mkdir(parents=True, exist_ok=True)

    features = pd.concat([styles.video_features(cache, v) for v in data.all_videos()], ignore_index=True)
    features.round(4).to_csv(out / "style_features.csv", index=False, lineterminator="\n")
    z = styles.standardise(features)
    check = style_check(z)
    (out / "style_check.md").write_text(render_style_check(features, z, check), encoding="utf-8", newline="\n")
    print("style check written; stable:", is_stable(check), flush=True)
    if not is_stable(check):
        return 2
    if args.check_only:
        return 0

    weights = pd.read_csv(out / "blend_weights.csv")
    weights = weights[weights["kind"] == "used"]
    videos = [evaluate.load_video(cache, v) for v in data.all_videos()]
    table = run_all(videos, z, weights, args, same_experiment=False)
    print("main run done", flush=True)
    table_same = run_all(videos, z, weights, args, same_experiment=True)
    summary = evaluate.across_videos(table)
    diff = evaluate.paired_differences(table)
    diff_same = evaluate.paired_differences(table_same)
    table.round(4).to_csv(out / "chosen_vs_random_per_video.csv", index=False, lineterminator="\n")
    table_same.round(4).to_csv(out / "chosen_vs_random_same_experiment_per_video.csv", index=False, lineterminator="\n")
    summary.round(4).to_csv(out / "chosen_vs_random.csv", index=False, lineterminator="\n")
    diff.round(4).to_csv(out / "chosen_vs_random_diff.csv", index=False, lineterminator="\n")
    diff_same.round(4).to_csv(out / "chosen_vs_random_same_experiment_diff.csv", index=False, lineterminator="\n")
    (out / "chosen_vs_random.md").write_text(render(summary, diff, diff_same, args), encoding="utf-8", newline="\n")
    figure(summary, diff, out / "chosen_vs_random.png", args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
