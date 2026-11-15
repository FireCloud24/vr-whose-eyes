"""Check that viewer folder numbers mean the same person across videos.

    python scripts/check_ids.py

Writes results/id_linkage.md (the evidence and a verdict worked out from it) and
results/sittings.csv (one row per experiment and viewer). Exits with status 1 if
the within-experiment link fails, because nothing else in the project makes
sense without it.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from src import data, linkage


def folder_counts(root: Path) -> dict:
    """What is on disk: viewer folders and files per experiment, and the demographics rows."""
    out = {}
    for e in data.EXPERIMENTS:
        folders = sorted(int(p.name) for p in (Path(root) / f"Experiment_{e}").iterdir() if p.is_dir())
        files = sum(len(list((Path(root) / f"Experiment_{e}" / str(v)).glob("video_*.csv"))) for v in folders)
        out[e] = {"folders": folders, "files": files}
    out["demographics"] = sorted(data.read_viewers(root)["viewer"].tolist())
    return out


def verdict(counts: dict, sit: pd.DataFrame, overlaps: int, order: dict, height: dict) -> dict:
    """Turn the evidence into plain statements. Nothing here is decided in advance."""
    same_folders = counts[1]["folders"] == counts[2]["folders"] == counts["demographics"]
    complete = all(counts[e]["files"] == len(counts[e]["folders"]) * data.VIDEOS_PER_EXPERIMENT for e in data.EXPERIMENTS)
    share_one_sitting = float(sit["one_sitting"].mean())
    within = bool(same_folders and complete and share_one_sitting >= 0.95 and overlaps == 0)
    # Across experiments the recordings can only support the link, not prove it.
    renumbered_by_arrival = order[1] > 0.9 and order[2] > 0.9
    across_support = bool(not renumbered_by_arrival and height["across_experiments_p"] < 0.05)
    return {
        "same_folders": same_folders,
        "complete": complete,
        "share_one_sitting": share_one_sitting,
        "within_experiment_link": within,
        "across_experiment_support": across_support,
    }


def render(counts, sit, overlaps, order, height, v) -> str:
    odd = sit[~sit["one_sitting"]]
    lines = [
        "# Do viewer IDs link across videos?",
        "",
        "Written by `scripts/check_ids.py`. The files carry no name or device id, so this",
        "is the evidence the recordings themselves give.",
        "",
        "## What is on disk",
        "",
        "| | Viewer folders | Session files |",
        "|---|---|---|",
    ]
    for e in data.EXPERIMENTS:
        f = counts[e]["folders"]
        lines.append(f"| Experiment {e} | {len(f)} (numbered {f[0]} to {f[-1]}) | {counts[e]['files']} |")
    lines += [
        "",
        f"The single demographics file lists {len(counts['demographics'])} viewers. "
        + ("Its numbers match the folder numbers in both experiments." if v["same_folders"]
           else "Its numbers do NOT match the folder numbers in both experiments."),
        "",
        "## Within an experiment",
        "",
        f"- {int(sit['one_sitting'].sum())} of {len(sit)} folders are one sitting: nine videos recorded in play order",
        f"  within two hours. The median sitting lasted {sit.loc[sit['one_sitting'], 'span_minutes'].median():.0f} minutes.",
        f"- Pairs of sessions from different folders that overlap in time: {overlaps}.",
        "  There was one headset, so an overlap would mean the clocks or the folders are wrong.",
    ]
    if len(odd):
        lines += ["- Folders that are not one clean sitting:", "",
                  "| Experiment | Viewer | Videos | In play order | Span (minutes) |", "|---|---|---|---|---|"]
        for r in odd.itertuples():
            lines.append(f"| {r.experiment} | {r.viewer} | {r.videos} | {'yes' if r.in_play_order else 'no'} | {r.span_minutes:.0f} |")
        lines += ["", "  These look like one video recorded again later. I keep them."]
    lines += [
        "",
        "## Across the two experiments",
        "",
        "The paper says 48 participants took part in the experiments, and it ships one",
        "demographics file for both. It never says in so many words that folder 17 is the",
        "same person in both. The recordings add this:",
        "",
        "| Check | Value |",
        "|---|---|",
        f"| Rank correlation of folder number with recording order, experiment 1 | {order[1]:.2f} |",
        f"| Rank correlation of folder number with recording order, experiment 2 | {order[2]:.2f} |",
        f"| Headset height, odd vs even videos of one sitting, experiment 1 (r) | {height['within_experiment_1_r']:.2f} |",
        f"| Headset height, odd vs even videos of one sitting, experiment 2 (r) | {height['within_experiment_2_r']:.2f} |",
        f"| Headset height, experiment 1 vs experiment 2 (r) | {height['across_experiments_r']:.2f} |",
        f"| Permutation p-value for that correlation being above zero | {height['across_experiments_p']:.4f} |",
        "",
        "How to read it. If numbers had been handed out afresh as people arrived, folder",
        "number would follow recording order in both experiments. Headset height is a",
        "weak trace of a person: it also depends on the chair and on how the tracking was",
        "set up that day, so I expect a modest correlation across experiments at best.",
        "",
        "## Verdict",
        "",
        ("- Within an experiment, a folder is one person. " if v["within_experiment_link"]
         else "- Within an experiment, the link FAILED. ")
        + f"{100 * v['share_one_sitting']:.0f}% of folders are one sitting and {overlaps} sessions overlap.",
        ("- Across experiments, the recordings support the link but cannot prove it: folder numbers are not "
         "simply arrival order in both experiments, and headset height agrees more than chance."
         if v["across_experiment_support"] else
         "- Across experiments, the recordings do NOT support the link. Treat the experiments as separate viewer sets."),
        "- So every result that carries a viewer's style across experiments should also be",
        "  shown using videos from the same experiment only.",
        "",
    ]
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=str(data.RAW_ROOT))
    p.add_argument("--out", default="results")
    args = p.parse_args(argv)
    root, out = Path(args.root), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    counts = folder_counts(root)
    sessions = linkage.session_table(root)
    sit = linkage.sittings(sessions)
    overlaps = linkage.overlapping_pairs(sessions)
    order = {e: linkage.arrival_order_correlation(sit, e) for e in data.EXPERIMENTS}
    height = linkage.height_agreement(sessions)
    v = verdict(counts, sit, overlaps, order, height)

    sit.assign(span_minutes=sit["span_minutes"].round(2)).to_csv(out / "sittings.csv", index=False, lineterminator="\n")
    (out / "id_linkage.md").write_text(render(counts, sit, overlaps, order, height, v), encoding="utf-8", newline="\n")
    print(f"within-experiment link: {v['within_experiment_link']}; across-experiment support: {v['across_experiment_support']}")
    return 0 if v["within_experiment_link"] else 1


if __name__ == "__main__":
    sys.exit(main())
