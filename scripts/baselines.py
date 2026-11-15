"""Baselines: own motion, a crowd of k random viewers, and a blend of the two.

    python scripts/baselines.py

This is the "how many viewers" curve. For every video it runs the trial loop in
src/evaluate.py with random groups of k = 1, 2, 4, 8, 16, 32.

The blend needs one number per group size and horizon: how much weight to put
on the viewer's own motion. For each test video I pick the weight that did best
on the other 17 videos, so the test video never tunes its own blend.

Writes:
  results/budget.md / budget.csv        how the tile budget was chosen
  results/blend_weights.csv             coverage for every candidate weight, and the weight used per test video
  results/baselines_per_video.csv       one row per video, k and method
  results/baselines.csv / .md           mean over videos with 95% bootstrap intervals
  results/crowd_curve.png               the figure
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

from src import data, evaluate, metrics, parse, predict

WEIGHT_GRID = (0.1, 0.3, 0.5, 0.7, 0.9)
BUDGET_CANDIDATES = (8, 12, 16, 20, 24)
BUDGET_RULE = 0.95  # smallest budget at which perfect foresight covers this much


def budget_table(videos: list[dict]) -> pd.DataFrame:
    """Coverage with perfect foresight: fetch the tiles the viewer really looked at."""
    rows = []
    for vd in videos:
        seg = vd["segments"]
        for n in BUDGET_CANDIDATES:
            cov = metrics.coverage(predict.choose_tiles(seg, n), seg)
            rows.append({"video": vd["video"], "budget": n, "perfect_foresight_coverage": float(np.nanmean(cov))})
    return pd.DataFrame(rows)


def pick_budget(table: pd.DataFrame, rule: float = BUDGET_RULE) -> int:
    mean = table.groupby("budget")["perfect_foresight_coverage"].mean()
    return int(mean[mean >= rule].index.min())


def sweep_one(vd: dict, ks, n_trials: int, seed: int, budget: int, n_test: int) -> list[dict]:
    """Blend coverage on one video for every candidate weight."""
    rows = []
    for weight in WEIGHT_GRID:
        weights = {k: {h: weight for h in predict.HORIZONS} for k in ks}
        trials = evaluate.run_video(vd, {"random": evaluate.random_group}, ks, n_trials, seed, budget, weights, n_test)
        blends = trials[trials["method"].str.startswith("blend_")]
        for (k, method), g in blends.groupby(["k", "method"]):
            rows.append({"video": vd["video"], "k": k, "horizon": int(method.split("_")[1]),
                         "own_weight": weight, "coverage": g["coverage"].mean()})
    return rows


def weight_sweep(videos: list[dict], ks, n_trials: int, seed: int, budget: int,
                 n_test: int = evaluate.N_TEST, jobs: int = 1) -> pd.DataFrame:
    """Mean coverage of the blend for every candidate weight: one row per video, k, horizon, weight."""
    tasks = [(vd, ks, n_trials, seed, budget, n_test) for vd in videos]
    return pd.DataFrame([row for rows in evaluate.run_parallel(sweep_one, tasks, jobs) for row in rows])


def evaluate_one(vd: dict, ks, n_trials: int, seed: int, budget: int, weights: dict, n_test: int) -> pd.DataFrame:
    return evaluate.run_video(vd, {"random": evaluate.random_group}, ks, n_trials, seed, budget, weights, n_test)


def leave_one_video_out_weights(sweep: pd.DataFrame) -> pd.DataFrame:
    """For each test video, k and horizon: the weight with the best mean coverage on the other videos."""
    rows = []
    for video in sweep["video"].unique():
        others = sweep[sweep["video"] != video]
        mean = others.groupby(["k", "horizon", "own_weight"])["coverage"].mean().reset_index()
        best = mean.loc[mean.groupby(["k", "horizon"])["coverage"].idxmax()]
        for r in best.itertuples():
            rows.append({"video": video, "k": r.k, "horizon": r.horizon, "own_weight": r.own_weight})
    return pd.DataFrame(rows)


def weights_for(chosen: pd.DataFrame, video: str) -> dict:
    """{k: {horizon: weight}} for one test video."""
    out: dict = {}
    for r in chosen[chosen["video"] == video].itertuples():
        out.setdefault(int(r.k), {})[int(r.horizon)] = float(r.own_weight)
    return out


def render_budget(table: pd.DataFrame, budget: int) -> str:
    mean = table.groupby("budget")["perfect_foresight_coverage"].agg(["mean", "min"])
    lines = [
        "# Choosing the tile budget",
        "",
        "Written by `scripts/baselines.py`. The frame has 72 tiles. With perfect foresight,",
        "meaning the system fetches exactly the tiles the viewer goes on to look at, this is",
        "the share of the viewer's window that a budget can cover:",
        "",
        "| Budget (tiles) | Share of the frame | Mean over videos | Lowest video |",
        "|---|---|---|---|",
    ]
    for n, r in mean.iterrows():
        lines.append(f"| {n} | {100 * n / 72:.0f}% | {100 * r['mean']:.1f}% | {100 * r['min']:.1f}% |")
    lines += [
        "",
        "Rule: take the smallest budget where perfect foresight covers at least",
        f"{100 * BUDGET_RULE:.0f}%. That is **{budget} tiles**. The rule looks only at perfect foresight, never at how a",
        "predictor scores. A smaller budget cannot serve even a perfectly predicted viewer, and a",
        "larger one makes every predictor look good.",
        "",
    ]
    return "\n".join(lines)


def fmt(row, metric: str, scale: float = 100, digits: int = 1) -> str:
    return f"{scale * row[metric]:.{digits}f} ({scale * row[metric + '_lo']:.{digits}f} to {scale * row[metric + '_hi']:.{digits}f})"


def render(summary: pd.DataFrame, used: pd.DataFrame, budget: int, n_trials: int) -> str:
    s = summary.set_index(["method", "k"])
    lines = [
        "# Baselines: own motion, random crowds, and a blend",
        "",
        f"Written by `scripts/baselines.py`. Budget {budget} of 72 tiles. Each video is a held-out test:",
        f"{n_trials} random splits into 16 test viewers and a pool of 32, with groups drawn at random from the",
        "pool. Numbers are means over the 18 videos with 95% bootstrap intervals over videos.",
        "Coverage is the share of the viewer's window in high quality. \"Poor seconds\" are",
        f"seconds per minute with coverage under {100 * metrics.POOR_BELOW:.0f}%.",
        "",
        "## Own motion (no other viewers)",
        "",
        "| Horizon | Coverage % | Worst 10% of viewers, coverage % | Poor seconds per minute | Worst 10%, poor seconds |",
        "|---|---|---|---|---|",
    ]
    for h in predict.HORIZONS:
        r = s.loc[(f"own_{h}", 0)]
        lines.append(f"| {h} s | {fmt(r, 'coverage')} | {fmt(r, 'coverage_worst10')} | {fmt(r, 'poor_s_per_min', 1)} | {fmt(r, 'poor_s_per_min_worst10', 1)} |")
    lines += ["", "## Crowd of k random viewers (same at every horizon)", "",
              "| k | Coverage % | Worst 10% of viewers, coverage % | Poor seconds per minute | Worst 10%, poor seconds |", "|---|---|---|---|---|"]
    for k in sorted(summary.loc[summary["method"] == "crowd", "k"]):
        r = s.loc[("crowd", k)]
        lines.append(f"| {k} | {fmt(r, 'coverage')} | {fmt(r, 'coverage_worst10')} | {fmt(r, 'poor_s_per_min', 1)} | {fmt(r, 'poor_s_per_min_worst10', 1)} |")
    lines += ["", "## Blend of own motion and the crowd: coverage %", "",
              "| k | " + " | ".join(f"{h} s ahead" for h in predict.HORIZONS) + " |", "|---|" + "---|" * len(predict.HORIZONS)]
    for k in sorted(summary.loc[summary["method"] == "crowd", "k"]):
        lines.append(f"| {k} | " + " | ".join(fmt(s.loc[(f'blend_{h}', k)], "coverage") for h in predict.HORIZONS) + " |")
    lines += ["", "## Weight on own motion in the blend", "",
              "Chosen for each test video from the other 17 videos. The table shows the most common choice",
              "across test videos.", "",
              "| k | " + " | ".join(f"{h} s ahead" for h in predict.HORIZONS) + " |", "|---|" + "---|" * len(predict.HORIZONS)]
    mode = used.groupby(["k", "horizon"])["own_weight"].agg(lambda x: x.mode().iloc[0])
    for k in sorted(used["k"].unique()):
        lines.append(f"| {k} | " + " | ".join(f"{mode.loc[(k, h)]:.1f}" for h in predict.HORIZONS) + " |")
    lines.append("")
    return "\n".join(lines)


def figure(summary: pd.DataFrame, path: Path, budget: int):
    s = summary.set_index(["method", "k"])
    ks = sorted(summary.loc[summary["method"] == "crowd", "k"])
    colours = {1: "#1b9e77", 2: "#d95f02", 5: "#7570b3"}
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    for ax, metric, label in ((axes[0], "coverage", "Coverage, average viewer (%)"),
                              (axes[1], "coverage_worst10", "Coverage, worst-served 10% of viewers (%)")):
        crowd = s.loc[[("crowd", k) for k in ks]]
        ax.plot(ks, 100 * crowd[metric], "o-", color="black", label="crowd of k random viewers")
        ax.fill_between(ks, 100 * crowd[f"{metric}_lo"], 100 * crowd[f"{metric}_hi"], color="black", alpha=0.12, lw=0)
        for h in predict.HORIZONS:
            own = s.loc[(f"own_{h}", 0)]
            ax.axhline(100 * own[metric], color=colours[h], ls="--", lw=1.2, label=f"own motion, {h} s ahead")
            blend = s.loc[[(f"blend_{h}", k) for k in ks]]
            ax.plot(ks, 100 * blend[metric], "s-", color=colours[h], ms=4, lw=1.2, label=f"blend, {h} s ahead")
        ax.set_xscale("log", base=2)
        ax.set_xticks(ks)
        ax.set_xticklabels([str(k) for k in ks])
        ax.set_xlabel("earlier viewers in the crowd (k)")
        ax.set_ylabel(label)
        ax.grid(alpha=0.25)
    axes[0].legend(fontsize=7, loc="lower right")
    fig.suptitle(f"Coverage with {budget} of 72 tiles, mean over 18 held-out videos (band: 95% interval over videos)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", default=str(parse.PROCESSED))
    p.add_argument("--out", default="results")
    p.add_argument("--trials", type=int, default=200)
    p.add_argument("--tuning-trials", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--ks", type=int, nargs="*", default=list(evaluate.KS))
    p.add_argument("--n-test", type=int, default=evaluate.N_TEST)
    p.add_argument("--jobs", type=int, default=6, help="videos evaluated in parallel")
    args = p.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    videos = [evaluate.load_video(Path(args.cache), v) for v in data.all_videos()]
    budgets = budget_table(videos)
    budget = pick_budget(budgets)
    budgets.round(4).to_csv(out / "budget.csv", index=False, lineterminator="\n")
    (out / "budget.md").write_text(render_budget(budgets, budget), encoding="utf-8", newline="\n")
    print(f"budget: {budget} tiles", flush=True)

    # A different seed for tuning, so the weights are not tuned on the evaluation splits.
    sweep = weight_sweep(videos, args.ks, args.tuning_trials, args.seed + 1000, budget, args.n_test, args.jobs)
    used = leave_one_video_out_weights(sweep)
    pd.concat([sweep.assign(kind="candidate"), used.assign(kind="used")]).round(4).to_csv(
        out / "blend_weights.csv", index=False, lineterminator="\n")
    print("blend weights chosen", flush=True)

    tasks = [(vd, args.ks, args.trials, args.seed + i, budget, weights_for(used, vd["video"]), args.n_test)
             for i, vd in enumerate(videos)]
    trials = evaluate.run_parallel(evaluate_one, tasks, args.jobs)
    table = evaluate.per_video(pd.concat(trials))
    summary = evaluate.across_videos(table)
    table.round(4).to_csv(out / "baselines_per_video.csv", index=False, lineterminator="\n")
    summary.round(4).to_csv(out / "baselines.csv", index=False, lineterminator="\n")
    (out / "baselines.md").write_text(render(summary, used, budget, args.trials), encoding="utf-8", newline="\n")
    figure(summary, out / "crowd_curve.png", budget)
    return 0


if __name__ == "__main__":
    sys.exit(main())
