"""Can four chosen viewers beat sixteen random ones?

    python scripts/four_vs_sixteen.py

Reads results/chosen_vs_random_per_video.csv (written by scripts/chosen_vs_random.py),
so the comparison uses the same trials: same splits, same test viewers. For each
held-out video it takes the difference between a group of 4 and a random group
of 16, then gives the mean over videos with a 95% bootstrap interval over videos.

It also answers "how many random viewers is a chosen group of 4 worth?" by
reading the random-group curve backwards.

Writes results/four_vs_sixteen.csv, .md and .png. The verdict sentences in the
.md are worked out from the intervals, not written in advance.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import evaluate

SMALL, LARGE = 4, 16
ARMS = ("mixed", "typical", "random")
METHODS = (("crowd", "crowd only"), ("blend_2", "blend, 2 s ahead"), ("blend_5", "blend, 5 s ahead"))
SHOWN = (("coverage", "Coverage, average viewer (points)", 100, True),
         ("coverage_worst10", "Coverage, worst 10% of viewers (points)", 100, True),
         ("poor_s_per_min_worst10", "Poor seconds per minute, worst 10%", 1, False))


def comparison(table: pd.DataFrame, n_boot: int = 10000) -> pd.DataFrame:
    """Groups of SMALL (every arm) minus a random group of LARGE, paired by video."""
    d = evaluate.paired_differences(table, baseline=("random", LARGE), n_boot=n_boot)
    return d[d["k"] == SMALL].reset_index(drop=True)


def by_experiment(table: pd.DataFrame, n_boot: int = 10000) -> pd.DataFrame:
    parts = []
    for e in ("1", "2"):
        part = comparison(table[table["video"].str.startswith(e + "-")], n_boot)
        part.insert(0, "experiment", int(e))
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def verdict(lo: float, hi: float, higher_is_better: bool) -> str:
    """Words for an interval of (four minus sixteen)."""
    if not higher_is_better:
        lo, hi = -hi, -lo
    if lo > 0:
        return "four beat sixteen"
    if hi < 0:
        return "sixteen beat four"
    return "no clear difference"


def equivalent_random_k(table: pd.DataFrame, arm: str, method: str, metric: str = "coverage") -> float:
    """The size of random group that scores the same as `arm` at k = SMALL, by straight-line
    interpolation of the random curve on a log scale of k. Clipped to the range of k tried."""
    mean = table[table["method"] == method].groupby(["arm", "k"])[metric].mean()
    target = mean.loc[(arm, SMALL)]
    curve = mean.loc["random"].sort_index()
    ks, values = np.log2(curve.index.to_numpy(float)), curve.to_numpy()
    if not (np.diff(values) > 0).all():
        values = np.maximum.accumulate(values)
    return float(2 ** np.interp(target, values, ks))


def render(d: pd.DataFrame, per_exp: pd.DataFrame, equiv: dict, n_videos: int) -> str:
    idx = d.set_index(["arm", "method", "metric"])
    lines = [
        f"# {SMALL} chosen viewers against {LARGE} random viewers",
        "",
        "Written by `scripts/four_vs_sixteen.py` from the same trials as `chosen_vs_random.md`.",
        f"Each number is (group of {SMALL}) minus (random group of {LARGE}), averaged over {n_videos} held-out videos, with a",
        "95% bootstrap interval over videos and the count of videos where the group of four did better.",
        "",
    ]
    for method, label in METHODS:
        lines += [f"## {label.capitalize()}", "",
                  f"| Group of {SMALL} | " + " | ".join(name for _, name, _, _ in SHOWN) + " | Verdict on average coverage |",
                  "|---|" + "---|" * (len(SHOWN) + 1)]
        for arm in ARMS:
            cells = []
            for metric, _, scale, higher in SHOWN:
                r = idx.loc[(arm, method, metric)]
                better = r["videos_above_zero"] if higher else r["videos"] - r["videos_above_zero"]
                cells.append(f"{scale * r['difference']:+.1f} ({scale * r['lo']:+.1f} to {scale * r['hi']:+.1f}), {better}/{r['videos']}")
            r = idx.loc[(arm, method, "coverage")]
            lines.append(f"| {arm} | " + " | ".join(cells) + f" | {verdict(r['lo'], r['hi'], True)} |")
        lines.append("")
    lines += ["## How many random viewers is a group of four worth?", "",
              "Read off the random-group curve for average coverage, crowd only. A value of 4 means the",
              "choice added nothing. The curve was measured from 1 to 32 viewers, so values stop there.", "",
              "| Group of 4 | Equivalent number of random viewers |", "|---|---|"]
    for arm in ARMS[:2]:
        lines.append(f"| {arm} | {equiv[arm]:.1f} |")
    e = per_exp[(per_exp["method"] == "crowd") & (per_exp["metric"] == "coverage")].set_index(["experiment", "arm"])
    lines += ["", "## By experiment (crowd only, average coverage, points)", "",
              "Nine videos each, so these intervals are wide.", "",
              "| Group of 4 | Experiment 1 (free viewing) | Experiment 2 (live events, told to follow) |", "|---|---|---|"]
    for arm in ARMS:
        cells = [f"{100 * e.loc[(x, arm), 'difference']:+.1f} ({100 * e.loc[(x, arm), 'lo']:+.1f} to {100 * e.loc[(x, arm), 'hi']:+.1f})" for x in (1, 2)]
        lines.append(f"| {arm} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def figure(d: pd.DataFrame, path: Path):
    idx = d.set_index(["arm", "method", "metric"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    colours = {"mixed": "#d95f02", "typical": "#1b9e77", "random": "black"}
    for ax, (metric, label) in zip(axes, (("coverage", "average viewer"), ("coverage_worst10", "worst-served 10% of viewers"))):
        ax.axvline(0, color="black", lw=0.8)
        y, ticks = 0, []
        for method, mlabel in METHODS:
            for arm in ARMS:
                r = idx.loc[(arm, method, metric)]
                ax.errorbar(100 * r["difference"], y, xerr=[[100 * (r["difference"] - r["lo"])], [100 * (r["hi"] - r["difference"])]],
                            fmt="o", color=colours[arm], capsize=3, ms=5)
                ticks.append((y, f"{arm} {SMALL}, {mlabel}"))
                y -= 1
            y -= 0.6
        ax.set_yticks([t for t, _ in ticks])
        ax.set_yticklabels([name for _, name in ticks], fontsize=7)
        ax.set_xlabel(f"coverage, {label}: group of {SMALL} minus {LARGE} random (points)", fontsize=8)
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle(f"A group of {SMALL} against {LARGE} random viewers, same tile budget (95% interval over 18 held-out videos)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="results")
    args = p.parse_args(argv)
    out = Path(args.out)
    table = pd.read_csv(out / "chosen_vs_random_per_video.csv")
    d = comparison(table)
    per_exp = by_experiment(table)
    equiv = {arm: equivalent_random_k(table, arm, "crowd") for arm in ARMS[:2]}
    pd.concat([d.assign(experiment="both"), per_exp]).round(4).to_csv(out / "four_vs_sixteen.csv", index=False, lineterminator="\n")
    (out / "four_vs_sixteen.md").write_text(render(d, per_exp, equiv, table["video"].nunique()), encoding="utf-8", newline="\n")
    figure(d, out / "four_vs_sixteen.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
