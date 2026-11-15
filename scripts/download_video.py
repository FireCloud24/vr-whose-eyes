"""Download one of the dataset's videos into data/videos/. Only the demo needs this.

    python scripts/download_video.py 1-2

The links come from the dataset's own videoMeta.csv files. The authors' page
gives a corrected link for video 2-9, because the one in the metadata points at
video 2-8. The authors publish no checksums, so the script records the size and
SHA-256 of what it got in data/videos/manifest.json. Videos are never committed.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts import download
from src import data

VIDEO_DIR = Path("data/videos")
CORRECTED = {"2-9": "https://www.dropbox.com/s/hp9rf9vs93in6zl/2-9-HeyVR.mp4?dl=1"}


def video_url(root: Path, video: str) -> str:
    """Direct-download link for a video id such as "1-2"."""
    if video in CORRECTED:
        return CORRECTED[video]
    meta = data.read_video_meta(root).set_index("video")
    link = str(meta.loc[video, "DropboxLink"])
    return link.replace("dl=0", "dl=1") if "dl=" in link else link + "?dl=1"


def fetch_video(root: Path, video: str, out_dir: Path = VIDEO_DIR, opener=None) -> Path:
    """Download unless already there. Returns the local path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{video}.mp4"
    manifest = download.load_manifest(out_dir)
    entry = manifest["files"].get(dest.name)
    if dest.exists() and entry and entry["bytes"] == dest.stat().st_size:
        print(f"skip  {dest.name} (already downloaded)")
        return dest
    url = video_url(root, video)
    print(f"fetch {dest.name}")
    download.fetch(url, dest, *([opener] if opener else []))
    manifest["files"][dest.name] = {"url": url, "sha256": download.sha256_of(dest), "bytes": dest.stat().st_size}
    download.save_manifest(out_dir, manifest)
    return dest


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", help='video id, for example "1-2"')
    p.add_argument("--root", default=str(data.RAW_ROOT))
    p.add_argument("--out", default=str(VIDEO_DIR))
    args = p.parse_args(argv)
    path = fetch_video(Path(args.root), args.video, Path(args.out))
    print(f"{path} ({path.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
