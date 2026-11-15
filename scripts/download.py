"""Download the head-tracking dataset into data/raw/ and unpack it.

Wu, Tan, Wang and Yang, "A Dataset for Exploring User Behaviors in VR Spherical
Video Streaming", MMSys 2017. The authors link one zip from
https://wuchlei-thu.github.io. It holds the head-tracking logs only: 48 viewer
folders in each of two experiments, 9 videos each, plus two small metadata files.
The videos themselves are separate downloads and are not needed until the demo.

    python scripts/download.py

The authors publish no checksum. The SHA-256 below is the one I got on
2026-11-14, so a later run fails loudly if the file ever changes. The data is
never committed. Re-running skips anything already downloaded and verified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ARCHIVE = {
    "name": "vr-dataset.zip",
    "url": "https://www.dropbox.com/s/aqk6sbwqw6jyqck/vr-dataset.zip?dl=1",
    "sha256": "02e5f2cb570baae9d86355165dc24a8c351eefb195aaaa81e95c28387f842ec3",
}
# The only paths the archive should contain. Anything else is ignored.
WANTED = re.compile(
    r"^Formated_Data/(userDemo\.csv|Experiment_[12]/videoMeta\.csv|Experiment_[12]/\d{1,2}/video_\d\.csv)$"
)
EXPECTED_FILES = 2 * 48 * 9 + 3
MANIFEST = "manifest.json"
USER_AGENT = "vr-whose-eyes-downloader/0.1 (research use)"
CHUNK = 1 << 20


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(raw_dir: Path) -> dict:
    path = raw_dir / MANIFEST
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"files": {}}


def save_manifest(raw_dir: Path, manifest: dict) -> None:
    (raw_dir / MANIFEST).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def fetch(url: str, dest: Path, opener=urllib.request.urlopen) -> None:
    """Stream url to a .part file, then rename it into place."""
    part = dest.with_name(dest.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener(req) as resp:
        done, last = 0, time.time()
        with open(part, "wb") as f:
            while chunk := resp.read(CHUNK):
                f.write(chunk)
                done += len(chunk)
                if time.time() - last > 10:
                    last = time.time()
                    print(f"    {done / 1e6:.0f} MB", flush=True)
    part.replace(dest)


def download_verified(raw_dir: Path, spec: dict, opener=urllib.request.urlopen) -> Path:
    """Fetch spec['url'] unless a verified copy exists. Raise if the SHA-256 is wrong."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(raw_dir)
    dest = raw_dir / spec["name"]
    entry = manifest["files"].get(spec["name"])
    if dest.exists() and entry and entry["sha256"] == spec["sha256"] and entry["bytes"] == dest.stat().st_size:
        print(f"skip  {spec['name']} (already downloaded and verified)")
        return dest
    if not dest.exists():
        print(f"fetch {spec['name']}")
        fetch(spec["url"], dest, opener)
    got = sha256_of(dest)
    if got != spec["sha256"]:
        raise ValueError(f"{spec['name']}: SHA-256 {got} does not match the recorded {spec['sha256']}")
    manifest["files"][spec["name"]] = {"url": spec["url"], "sha256": got, "bytes": dest.stat().st_size}
    save_manifest(raw_dir, manifest)
    return dest


def extract(archive: Path, out_dir: Path, wanted: re.Pattern = WANTED) -> list[str]:
    """Unpack the members whose path matches `wanted`, keeping the folder layout.
    The pattern allows no '..' and no absolute path, so nothing can land outside
    out_dir. Files already unpacked at the right size are left alone."""
    done = []
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir() or not wanted.match(info.filename):
                continue
            target = out_dir / info.filename
            if not target.exists() or target.stat().st_size != info.file_size:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as f:
                    while chunk := src.read(CHUNK):
                        f.write(chunk)
            done.append(info.filename)
    return done


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--raw-dir", default="data/raw")
    args = p.parse_args(argv)

    raw_dir = Path(args.raw_dir)
    archive = download_verified(raw_dir, ARCHIVE)
    names = extract(archive, raw_dir)
    print(f"unpacked {len(names)} files to {raw_dir}")
    if len(names) != EXPECTED_FILES:
        raise ValueError(f"expected {EXPECTED_FILES} files in the archive, found {len(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
