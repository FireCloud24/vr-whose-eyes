"""Parse every video, summarise the data, and draw one attention heatmap per video.

    python scripts/heatmaps.py

Writes:
  data/processed/{video}.npz        cached orientations and 6 x 12 tile weights
  results/data_summary.csv / .md    one row per video: length, missing data, how spread out attention is
  results/heatmaps/{video}.png      share of viewing time each part of the frame was on screen
  results/heatmaps/all_videos.png   the 18 heatmaps on one sheet

A heatmap value is the share of all viewer-seconds in which that part of the
frame was inside the viewer's window. The 6 x 12 tile grid is drawn on top.
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

from src import data, geometry, parse

FINE_ROWS, FINE_COLS = 36, 72  # 5 degree cells for drawing
FINE_EVERY = 10                # one tick a second is plenty for the drawing grid


def on_screen_share(q: np.ndarray) -> np.ndarray:
    """(viewers, ticks, 4) -> (FINE_ROWS, FINE_COLS): share of viewer-time each cell is on screen.
    Columns run left to right as in the real video frame."""
    # 40 rays a side, so every 5 degree cell inside the window is hit by a few rays.
    w = geometry.tile_weights(q[:, ::FINE_EVERY], FINE_ROWS, FINE_COLS, n=40, chunk=1000)
    flat = w.reshape(-1, FINE_ROWS, FINE_COLS)
    present = ~np.isnan(flat[:, 0, 0])
    grid = (flat[present] > 0).mean(axis=0)
    return grid[:, ::-1] if geometry.PICTURE_MIRRORED else grid  # drawn the way the video frame runs


def tile_concentration(weights: np.ndarray, top: int = 16) -> float:
    """Share of all viewing that lands on the `top` most-watched tiles of the video."""
    mean = np.nanmean(weights.reshape(-1, weights.shape[-1]), axis=0)
    return float(np.sort(mean)[::-1][:top].sum())


def summarise(video: str, v: dict, meta_row) -> dict:
    q, w = v["q"], v["weights"]
    f = geometry.forward(q)
    speed = geometry.angle_between(f[:, 1:], f[:, :-1]) * int(v["hz"])
    lat = np.degrees(np.arcsin(np.clip(f[..., 1], -1, 1)))
    return {
        "video": video,
        "title": meta_row["Content"],
        "category": meta_row["Category"],
        "viewers": q.shape[0],
        "seconds": q.shape[1] / int(v["hz"]),
        "missing_share": float(np.isnan(q).any(axis=-1).mean()),
        "median_head_speed_deg_s": float(np.nanmedian(speed)),
        "share_within_30deg_of_horizon": float((np.abs(lat[~np.isnan(lat)]) < 30).mean()),
        "share_on_top_16_tiles": tile_concentration(w),
    }


def draw(ax, grid: np.ndarray, title: str, vmax: float):
    im = ax.imshow(grid, extent=[0, 360, -90, 90], origin="upper", cmap="magma", vmin=0, vmax=vmax, aspect="equal")
    for x in np.arange(0, 361, 360 / geometry.COLS):
        ax.axvline(x, color="white", lw=0.3, alpha=0.5)
    for y in np.arange(-90, 91, 180 / geometry.ROWS):
        ax.axhline(y, color="white", lw=0.3, alpha=0.5)
    ax.set_title(title, fontsize=8)
    ax.set_xticks([0, 180, 360])
    ax.set_yticks([-90, 0, 90])
    ax.tick_params(labelsize=6)
    return im


def render_summary(table: pd.DataFrame) -> str:
    lines = [
        "# The data, one row per video",
        "",
        "Written by `scripts/heatmaps.py`. Every viewer is put on the video's own clock at",
        f"{parse.HZ} samples a second. \"Missing\" is the share of samples with no recorded row within",
        f"{parse.MAX_GAP_S} seconds. \"Top 16 tiles\" is the share of all viewing that lands on the 16",
        "most-watched of the 72 tiles, so a high value means everyone looks at the same place.",
        "",
        "| Video | Title | Category | Viewers | Length (s) | Missing | Median head speed (deg/s) | Within 30 deg of horizon | Top 16 tiles |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in table.itertuples():
        lines.append(f"| {r.video} | {r.title} | {r.category} | {r.viewers} | {r.seconds:.0f} | {100 * r.missing_share:.2f}% | "
                     f"{r.median_head_speed_deg_s:.1f} | {100 * r.share_within_30deg_of_horizon:.0f}% | {100 * r.share_on_top_16_tiles:.0f}% |")
    by = table.assign(experiment=table["video"].str[0]).groupby("experiment")
    lines += ["", "| Experiment | Videos | Total minutes | Median head speed (deg/s) | Top 16 tiles |", "|---|---|---|---|---|"]
    for e, g in by:
        lines.append(f"| {e} | {len(g)} | {g['seconds'].sum() / 60:.0f} | {g['median_head_speed_deg_s'].mean():.1f} | {100 * g['share_on_top_16_tiles'].mean():.0f}% |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=str(data.RAW_ROOT))
    p.add_argument("--cache", default=str(parse.PROCESSED))
    p.add_argument("--out", default="results")
    p.add_argument("--viewers", type=int, nargs="*", default=list(data.VIEWERS))
    args = p.parse_args(argv)
    out = Path(args.out)
    (out / "heatmaps").mkdir(parents=True, exist_ok=True)
    meta = data.read_video_meta(Path(args.root)).set_index("video")

    rows, grids = [], {}
    for video in data.all_videos():
        v = parse.cached_video(Path(args.root), video, Path(args.cache), tuple(args.viewers))
        rows.append(summarise(video, v, meta.loc[video]))
        grids[video] = on_screen_share(v["q"])
        print(f"{video}: {rows[-1]['seconds']:.0f} s, missing {100 * rows[-1]['missing_share']:.2f}%", flush=True)
    table = pd.DataFrame(rows)
    table.round(4).to_csv(out / "data_summary.csv", index=False, lineterminator="\n")
    (out / "data_summary.md").write_text(render_summary(table), encoding="utf-8", newline="\n")

    vmax = max(g.max() for g in grids.values())
    for video, grid in grids.items():
        fig, ax = plt.subplots(figsize=(5, 2.9))
        im = draw(ax, grid, f"{video}  {meta.loc[video, 'Content']}", vmax)
        ax.set_xlabel("across the video frame, left to right (degrees)", fontsize=7)
        ax.set_ylabel("latitude", fontsize=7)
        fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02).ax.tick_params(labelsize=6)
        fig.tight_layout()
        fig.savefig(out / "heatmaps" / f"{video}.png", dpi=110)
        plt.close(fig)
    fig, axes = plt.subplots(6, 3, figsize=(10, 12))
    for ax, (video, grid) in zip(axes.ravel(), grids.items()):  # experiment 1 is the top three rows
        im = draw(ax, grid, f"{video}  {meta.loc[video, 'Content']}", vmax)
    fig.suptitle("Share of viewing time each part of the frame was on screen (48 viewers per video)", fontsize=10)
    fig.tight_layout(rect=[0, 0, 0.93, 0.98])
    fig.colorbar(im, cax=fig.add_axes([0.94, 0.3, 0.012, 0.4])).ax.tick_params(labelsize=7)
    fig.savefig(out / "heatmaps" / "all_videos.png", dpi=110)
    plt.close(fig)
    return 0


if __name__ == "__main__":
    sys.exit(main())
