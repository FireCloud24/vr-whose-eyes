"""Two checks on the chosen-versus-random result.

    python scripts/why_not_mixed.py

1. Budget. With 16 tiles the budget is about one window, so a heatmap cannot
   serve two camps at once. If a mixed group only fails for lack of room, it
   should do better with 24 tiles. This reruns the three arms, crowd only, at 12
   and 24 tiles.

2. Who predicts whom. The diversity idea assumes that a calm viewer is best
   predicted by calm viewers and an active viewer by active viewers. Here every
   viewer gets an activity score from the other videos (the mean of the head
   speed and exploration z-scores). The pool is cut into thirds. A group of 4 is
   drawn from one third at a time and scored separately on calm, middle and
   active test viewers.

Writes results/why_not_mixed.md plus budget_check.csv and who_predicts_whom.csv.
"""
from __future__ import annotations

import argparse
import functools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from scripts import chosen_vs_random
from src import data, evaluate, metrics, parse, predict, styles

BUDGETS = (12, 24)
THIRDS = ("calm", "middle", "active")
GROUP = 4


def budget_one(vd: dict, style: np.ndarray, ks, n_trials: int, seed: int, budget: int, n_test: int) -> pd.DataFrame:
    arms = {"random": evaluate.random_group,
            "mixed": functools.partial(styles.mixed_group, style=style),
            "typical": functools.partial(styles.typical_group, style=style)}
    return evaluate.run_video(vd, arms, ks, n_trials, seed, budget, None, n_test)


def activity(style: pd.DataFrame) -> np.ndarray:
    """One number per viewer: mean of the head speed and exploration z-scores."""
    return style[["head_speed", "exploration"]].mean(axis=1).to_numpy()


def thirds(scores: np.ndarray, pool: np.ndarray) -> np.ndarray:
    """Label every viewer 0 (calm), 1 (middle) or 2 (active), with cut points taken from the pool."""
    lo, hi = np.quantile(scores[pool], [1 / 3, 2 / 3])
    return np.digitize(scores, [lo, hi])


def cross_one(vd: dict, scores: np.ndarray, n_trials: int, seed: int, budget: int, n_test: int) -> pd.DataFrame:
    """Mean coverage of test viewers in each third, by the third the group of 4 came from."""
    n = vd["segments"].shape[0]
    split_rng = np.random.default_rng([seed, 0])
    total, count = np.zeros((3, 3)), np.zeros((3, 3))
    for trial in range(n_trials):
        pool, test = evaluate.split_viewers(n, n_test, split_rng)
        label = thirds(scores, pool)
        rng = np.random.default_rng([seed, 2, trial])
        for source in range(3):
            members = pool[label[pool] == source]
            if len(members) < GROUP:
                continue
            group = rng.choice(members, size=GROUP, replace=False)
            cov = metrics.mean_coverage(evaluate.group_coverage(vd, group, test, budget)["crowd"], axis=1)
            for target in range(3):
                mine = label[test] == target
                if mine.any():
                    total[target, source] += cov[mine].mean()
                    count[target, source] += 1
    rows = [{"video": vd["video"], "test_viewers": THIRDS[t], "group_from": THIRDS[s], "coverage": total[t, s] / count[t, s]}
            for t in range(3) for s in range(3) if count[t, s] > 0]
    return pd.DataFrame(rows)


def cross_summary(cross: pd.DataFrame, n_boot: int = 10000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(cells, own-style advantage). Cells: mean coverage over videos with intervals.
    Advantage: for each kind of test viewer, coverage from a group of their own third
    minus the average from the other two thirds, paired by video."""
    cells = []
    for (t, s), g in cross.groupby(["test_viewers", "group_from"]):
        mean, lo, hi = evaluate.bootstrap_mean(g["coverage"], n_boot)
        cells.append({"test_viewers": t, "group_from": s, "coverage": mean, "lo": lo, "hi": hi, "videos": len(g)})
    wide = cross.pivot_table(index=["video", "test_viewers"], columns="group_from", values="coverage").reset_index()
    adv = []
    for t in THIRDS:
        g = wide[wide["test_viewers"] == t]
        others = [c for c in THIRDS if c != t]
        if g.empty or any(col not in g.columns for col in THIRDS):
            continue
        diff = (g[t] - g[others].mean(axis=1)).dropna().to_numpy()
        if len(diff) == 0:
            continue
        mean, lo, hi = evaluate.bootstrap_mean(diff, n_boot)
        adv.append({"test_viewers": t, "own_minus_others": mean, "lo": lo, "hi": hi, "videos": len(diff),
                    "videos_above_zero": int((diff > 0).sum())})
    return pd.DataFrame(cells), pd.DataFrame(adv)


def render(budget_diffs: dict, cells: pd.DataFrame, adv: pd.DataFrame, args) -> str:
    lines = [
        "# Why did the mixed group not help? Two checks",
        "",
        f"Written by `scripts/why_not_mixed.py`. Crowd only, {args.trials} trials per video, 18 held-out videos.",
        "",
        "## 1. Is it just the tight budget?",
        "",
        "Differences from a random group of the same size, as in `chosen_vs_random.md`, at other budgets.",
        "",
    ]
    for budget, diff in budget_diffs.items():
        lines += [f"### {budget} of 72 tiles", "", *chosen_vs_random.diff_table(diff, "crowd", [k for k in args.ks if k < 32]), ""]
    c = cells.set_index(["test_viewers", "group_from"])
    lines += [
        "## 2. Do viewers of one kind predict viewers of the same kind?",
        "",
        f"Coverage % of test viewers (rows) when the {GROUP} earlier viewers all come from one third of the pool",
        f"(columns), {args.budget} tiles. Thirds are by activity score from the other videos.",
        "",
        "| Test viewers | Group of calm viewers | Group of middle viewers | Group of active viewers |",
        "|---|---|---|---|",
    ]
    def cell(t, s):  # a third can be empty in a very small dataset
        if (t, s) not in c.index:
            return "no data"
        return f"{100 * c.loc[(t, s), 'coverage']:.1f} ({100 * c.loc[(t, s), 'lo']:.1f} to {100 * c.loc[(t, s), 'hi']:.1f})"

    for t in THIRDS:
        lines.append(f"| {t} | " + " | ".join(cell(t, s) for s in THIRDS) + " |")
    lines += ["", "Own kind minus the average of the other two kinds, paired by video (points, 95% interval, videos above zero):", "",
              "| Test viewers | Own kind minus others |", "|---|---|"]
    for r in adv.itertuples():
        lines.append(f"| {r.test_viewers} | {100 * r.own_minus_others:+.1f} ({100 * r.lo:+.1f} to {100 * r.hi:+.1f}), {r.videos_above_zero}/{r.videos} |")
    lines.append("")
    return "\n".join(lines)


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
    args = p.parse_args(argv)
    out, cache = Path(args.out), Path(args.cache)

    z = styles.standardise(pd.read_csv(out / "style_features.csv"))
    videos = [evaluate.load_video(cache, v) for v in data.all_videos()]
    style_tables = [styles.style_for(z, vd["video"]).loc[vd["viewers"]] for vd in videos]

    budget_diffs, rows = {}, []
    for budget in BUDGETS:
        tasks = [(vd, st.to_numpy(), args.ks, args.trials, args.seed + i, budget, args.n_test)
                 for i, (vd, st) in enumerate(zip(videos, style_tables))]
        table = evaluate.per_video(pd.concat(evaluate.run_parallel(budget_one, tasks, args.jobs)))
        budget_diffs[budget] = evaluate.paired_differences(table)
        rows.append(budget_diffs[budget].assign(budget=budget))
        print(f"budget {budget} done", flush=True)
    pd.concat(rows).round(4).to_csv(out / "budget_check.csv", index=False, lineterminator="\n")

    tasks = [(vd, activity(st), args.trials, args.seed + i, args.budget, args.n_test)
             for i, (vd, st) in enumerate(zip(videos, style_tables))]
    cross = pd.concat(evaluate.run_parallel(cross_one, tasks, args.jobs), ignore_index=True)
    cells, adv = cross_summary(cross)
    pd.concat([cells.assign(kind="cell"), adv.assign(kind="own_minus_others")]).round(4).to_csv(
        out / "who_predicts_whom.csv", index=False, lineterminator="\n")
    (out / "why_not_mixed.md").write_text(render(budget_diffs, cells, adv, args), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
