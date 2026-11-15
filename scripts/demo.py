"""Side-by-side demo: one viewer, one clip, the same tile budget, two ways of picking the crowd.

    python scripts/download_video.py 1-2
    python scripts/demo.py --video 1-2 --viewer 7 --start 60 --seconds 10 --left mixed:4 --right random:16

Each half shows what the viewer's headset would show if the 16 high-quality
tiles had been picked from that group's heatmap. Tiles outside the 16 are drawn
blocky to stand for low quality. Under each view is the whole frame with the
chosen tiles sharp and the viewer's window outlined.

The groups come from one trial of the same loop the results use: a random split
in which this viewer is a test viewer, and groups picked from the pool only.

Writes results/demo.gif and results/demo.md (what the clip shows, with its numbers).
Needs ffmpeg on the path to read frames from the video.
"""
from __future__ import annotations

import argparse
import functools
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from src import data, evaluate, geometry, metrics, parse, predict, render, styles

FPS = 10            # frames read from the video per second
GIF_FPS = 5         # frames kept in the GIF per second
VIEW = 300          # size of each headset view in pixels
FRAME_W, FRAME_H = 1200, 600
ARM_TEXT = {"random": "random viewers", "mixed": "viewers mixed by style", "typical": "most typical viewers"}


def find_trial(n_viewers: int, viewer_row: int, seed: int, n_test: int = evaluate.N_TEST) -> tuple[np.ndarray, np.ndarray, int]:
    """The first split from this seed's sequence in which the viewer is a test viewer."""
    rng = np.random.default_rng([seed, 0])
    for trial in range(10000):
        pool, test = evaluate.split_viewers(n_viewers, n_test, rng)
        if viewer_row in test:
            return pool, test, trial
    raise RuntimeError("no split found with this viewer in the test set")


def parse_side(text: str) -> tuple[str, int]:
    """"mixed:4" -> ("mixed", 4)."""
    arm, k = text.split(":")
    if arm not in ARM_TEXT:
        raise ValueError(f"unknown arm {arm!r}")
    return arm, int(k)


def pick_groups(sides: list[tuple[str, int]], pool: np.ndarray, seed: int, trial: int, style: np.ndarray) -> dict:
    """The same pickers and random streams as src/evaluate.run_video, so these are
    the very groups that trial used in the results."""
    import zlib
    pickers = {"random": evaluate.random_group,
               "mixed": functools.partial(styles.mixed_group, style=style),
               "typical": functools.partial(styles.typical_group, style=style)}
    return {(arm, k): pickers[arm](pool, k, np.random.default_rng([seed, 1, zlib.crc32(arm.encode()), k, trial])) for arm, k in sides}


def extract_frames(video_path: Path, start: float, seconds: float, out_dir: Path, fps: int = FPS) -> list[Path]:
    """Frames of the clip as equirectangular JPEGs, via ffmpeg."""
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(seconds), "-i", str(video_path),
                    "-vf", f"fps={fps},scale={FRAME_W}:{FRAME_H}", "-q:v", "3", str(out_dir / "%04d.jpg")], check=True)
    return sorted(out_dir.glob("*.jpg"))


def font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()


def panel(frame: np.ndarray, chosen: np.ndarray, q: np.ndarray, title: str, line: str) -> Image.Image:
    """One half of the demo: headset view on top, whole frame below, two lines of text."""
    shown = render.compose(frame, chosen)
    view = Image.fromarray(render.viewport_image(shown, q, VIEW))
    whole = Image.fromarray(render.outline_viewport(shown, q)).resize((VIEW, VIEW // 2), Image.BILINEAR)
    out = Image.new("RGB", (VIEW, VIEW + VIEW // 2 + 44), (0, 0, 0))
    out.paste(view, (0, 44))
    out.paste(whole, (0, 44 + VIEW))
    d = ImageDraw.Draw(out)
    d.text((6, 4), title, fill=(255, 255, 255), font=font(15))
    d.text((6, 24), line, fill=(255, 220, 120), font=font(13))
    return out


def build(video: str, viewer: int, start: int, seconds: int, sides: list[tuple[str, int]], seed: int,
          cache: Path, frames: list[Path], z_features: pd.DataFrame, budget: int = evaluate.BUDGET) -> tuple[list[Image.Image], dict]:
    """The GIF frames and the numbers behind them."""
    raw = np.load(Path(cache) / f"{video}.npz")
    vd = evaluate.load_video(cache, video)
    hz = int(raw["hz"])
    row = int(np.flatnonzero(vd["viewers"] == viewer)[0])
    style = styles.style_for(z_features, video).loc[vd["viewers"]].to_numpy()
    pool, test, trial = find_trial(len(vd["viewers"]), row, seed)
    groups = pick_groups(sides, pool, seed, trial, style)
    chosen = {side: predict.choose_tiles(predict.crowd_scores(vd["segments"], g), budget) for side, g in groups.items()}
    cov = {side: metrics.coverage(chosen[side], vd["segments"][row]) for side in sides}

    images = []
    for i, path in enumerate(frames):
        t = start + i / FPS
        segment = min(int(t), vd["segments"].shape[0] - 1)
        q = raw["q"][row, min(int(round(t * hz)), raw["q"].shape[1] - 1)]
        if np.isnan(q).any():
            continue
        frame = np.asarray(Image.open(path).convert("RGB"))
        halves = [panel(frame, chosen[side][segment], q, f"{side[1]} {ARM_TEXT[side[0]]}",
                        f"window in high quality: {100 * cov[side][segment]:.0f}%") for side in sides]
        sheet = Image.new("RGB", (2 * VIEW + 8, halves[0].height), (40, 40, 40))
        sheet.paste(halves[0], (0, 0))
        sheet.paste(halves[1], (VIEW + 8, 0))
        images.append(sheet)
    clip = slice(start, start + seconds)
    facts = {
        "video": video, "viewer": viewer, "start_s": start, "seconds": seconds, "budget": budget, "trial": trial, "seed": seed,
        **{f"group_{a}_{k}": " ".join(str(int(vd["viewers"][g])) for g in groups[(a, k)]) for a, k in sides},
        **{f"clip_coverage_{a}_{k}": float(np.nanmean(cov[(a, k)][clip])) for a, k in sides},
        **{f"video_coverage_{a}_{k}": float(np.nanmean(cov[(a, k)][evaluate.SKIP:])) for a, k in sides},
    }
    return images, facts


def render_note(facts: dict, sides: list[tuple[str, int]], title: str) -> str:
    lines = [
        "# What the demo clip shows",
        "",
        "Written by `scripts/demo.py`.",
        "",
        f"- Video {facts['video']} ({title}), seconds {facts['start_s']} to {facts['start_s'] + facts['seconds']}, seen through viewer {facts['viewer']}'s recorded head motion.",
        f"- Budget: {facts['budget']} of 72 tiles in high quality. Everything else is drawn blocky.",
        f"- Both groups come from the same pool of 32 earlier viewers. Viewer {facts['viewer']} is not in the pool.",
        "",
        "| Group | Viewers in it | Coverage in this clip | Coverage over the whole video |",
        "|---|---|---|---|",
    ]
    for a, k in sides:
        lines.append(f"| {k} {ARM_TEXT[a]} | {facts[f'group_{a}_{k}']} | {100 * facts[f'clip_coverage_{a}_{k}']:.0f}% | {100 * facts[f'video_coverage_{a}_{k}']:.0f}% |")
    lines += ["", "This is one viewer, one draw of the groups and a few seconds. It is an illustration of the",
              "set-up. The evidence is in `chosen_vs_random.md` and `four_vs_sixteen.md`.", ""]
    return "\n".join(lines)


def orientation_figure(frame: np.ndarray, q: np.ndarray, path: Path):
    """Evidence for which way round the picture runs: every viewer's view centre at one
    moment, drawn on the real frame under both readings. The right reading is the
    one that puts the cluster on something worth looking at."""
    u, v = geometry.frame_position(geometry.forward(q[~np.isnan(q).any(axis=1)]))
    h, w = frame.shape[:2]
    sheet = Image.new("RGB", (w, 2 * h + 4), (255, 255, 255))
    for i, (label, x) in enumerate((("picture x = u (my first reading of the paper)", u), ("picture x = 1 - u (mirrored)", 1 - u))):
        im = Image.fromarray(frame)
        d = ImageDraw.Draw(im)
        for cx, cy in zip(x * w, v * h):
            d.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], outline=(255, 40, 40), width=2)
        d.rectangle([0, 0, 8 * len(label) + 12, 22], fill=(0, 0, 0))
        d.text((6, 4), label, fill=(255, 255, 0), font=font(14))
        sheet.paste(im, (0, i * (h + 4)))
    sheet.save(path, quality=85)


def save_gif(images: list[Image.Image], path: Path, fps: int = GIF_FPS, colours: int = 64):
    """Keep every (FPS / fps)-th frame and a small palette, so the file stays a few megabytes."""
    images = images[::max(1, FPS // fps)]
    frames = [im.quantize(colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for im in images]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, optimize=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--video", required=True)
    p.add_argument("--viewer", type=int, required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--seconds", type=int, default=10)
    p.add_argument("--left", default="mixed:4", help="arm:k, for example mixed:4")
    p.add_argument("--right", default="random:16")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--cache", default=str(parse.PROCESSED))
    p.add_argument("--root", default=str(data.RAW_ROOT))
    p.add_argument("--video-dir", default="data/videos")
    p.add_argument("--out", default="results")
    p.add_argument("--orientation-second", type=int, default=None,
                   help="also write results/frame_orientation.jpg from this second of the video")
    args = p.parse_args(argv)
    out = Path(args.out)
    sides = [parse_side(args.left), parse_side(args.right)]
    z = styles.standardise(pd.read_csv(out / "style_features.csv"))
    with tempfile.TemporaryDirectory() as tmp:
        frames = extract_frames(Path(args.video_dir) / f"{args.video}.mp4", args.start, args.seconds, Path(tmp))
        images, facts = build(args.video, args.viewer, args.start, args.seconds, sides, args.seed, Path(args.cache), frames, z)
        if args.orientation_second is not None:
            still = extract_frames(Path(args.video_dir) / f"{args.video}.mp4", args.orientation_second, 0.1, Path(tmp) / "still")[0]
            raw = np.load(Path(args.cache) / f"{args.video}.npz")
            frame = np.asarray(Image.open(still).convert("RGB").resize((900, 450)))
            orientation_figure(frame, raw["q"][:, args.orientation_second * int(raw["hz"])], out / "frame_orientation.jpg")
    save_gif(images, out / "demo.gif")
    title = data.read_video_meta(Path(args.root)).set_index("video").loc[args.video, "Content"]
    pd.DataFrame([facts]).round(4).to_csv(out / "demo.csv", index=False, lineterminator="\n")
    (out / "demo.md").write_text(render_note(facts, sides, title), encoding="utf-8", newline="\n")
    print(f"{out / 'demo.gif'}: {len(images[::max(1, FPS // GIF_FPS)])} frames, {(out / 'demo.gif').stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
