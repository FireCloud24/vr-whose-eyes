"""The download script: verification, skipping and safe extraction. No network."""
import hashlib
import io
import zipfile

import pytest

from scripts import download


class FakeResponse(io.BytesIO):
    status = 200
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def opener_for(payload: bytes, calls: list):
    def opener(req):
        calls.append(req.full_url)
        return FakeResponse(payload)
    return opener


def spec_for(payload: bytes, name="file.bin"):
    return {"name": name, "url": "https://example.org/" + name, "sha256": hashlib.sha256(payload).hexdigest()}


def test_download_verifies_and_records(tmp_path):
    payload, calls = b"hello headset", []
    spec = spec_for(payload)
    path = download.download_verified(tmp_path, spec, opener_for(payload, calls))
    assert path.read_bytes() == payload
    assert download.load_manifest(tmp_path)["files"]["file.bin"]["sha256"] == spec["sha256"]
    assert calls == [spec["url"]]


def test_second_run_skips_the_fetch(tmp_path):
    payload, calls = b"abc", []
    spec = spec_for(payload)
    download.download_verified(tmp_path, spec, opener_for(payload, calls))
    download.download_verified(tmp_path, spec, opener_for(payload, calls))
    assert len(calls) == 1


def test_wrong_checksum_is_an_error(tmp_path):
    spec = spec_for(b"what I downloaded the first time")
    with pytest.raises(ValueError, match="SHA-256"):
        download.download_verified(tmp_path, spec, opener_for(b"something else", []))
    assert "file.bin" not in download.load_manifest(tmp_path)["files"]


def test_extract_keeps_layout_and_ignores_everything_else(tmp_path):
    archive = tmp_path / "a.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("Formated_Data/userDemo.csv", "No.,Gender\n1,Female\n")
        z.writestr("Formated_Data/Experiment_1/videoMeta.csv", "VideoNo\n1\n")
        z.writestr("Formated_Data/Experiment_2/12/video_3.csv", "Timestamp\n")
        z.writestr("Formated_Data/Experiment_3/1/video_0.csv", "not an experiment")
        z.writestr("Formated_Data/Experiment_1/1/notes.txt", "unwanted")
        z.writestr("../escape/video_0.csv", "outside")
        z.writestr("Formated_Data/Experiment_1/../../escape2/video_0.csv", "outside")
    out = tmp_path / "out"
    names = download.extract(archive, out)
    assert sorted(names) == [
        "Formated_Data/Experiment_1/videoMeta.csv",
        "Formated_Data/Experiment_2/12/video_3.csv",
        "Formated_Data/userDemo.csv",
    ]
    assert (out / "Formated_Data" / "Experiment_2" / "12" / "video_3.csv").read_text() == "Timestamp\n"
    assert not (tmp_path / "escape").exists() and not (tmp_path / "escape2").exists()
    assert sorted(p.name for p in (out / "Formated_Data").iterdir()) == ["Experiment_1", "Experiment_2", "userDemo.csv"]


def test_video_links_come_from_the_metadata_with_the_known_correction(tmp_path):
    from scripts import download_video
    from tests.conftest import make_dataset

    root = make_dataset(tmp_path / "Formated_Data", viewers=(1,), seconds=0.2)
    meta = root / "Experiment_1" / "videoMeta.csv"
    meta.write_text(meta.read_text().replace("https://example.org,https://example.org", "https://example.org,https://example.org/clip.mp4?dl=0", 1))
    assert download_video.video_url(root, "1-1") == "https://example.org/clip.mp4?dl=1"
    assert download_video.video_url(root, "1-2") == "https://example.org?dl=1"
    assert "2-9-HeyVR" in download_video.video_url(root, "2-9")


def test_fetch_video_downloads_once_and_records_what_it_got(tmp_path):
    from scripts import download_video
    from tests.conftest import make_dataset

    root = make_dataset(tmp_path / "Formated_Data", viewers=(1,), seconds=0.2)
    calls, payload = [], b"not really a video"
    out = tmp_path / "videos"
    path = download_video.fetch_video(root, "1-3", out, opener_for(payload, calls))
    assert path.name == "1-3.mp4" and path.read_bytes() == payload
    entry = download.load_manifest(out)["files"]["1-3.mp4"]
    assert entry["bytes"] == len(payload) and entry["sha256"] == hashlib.sha256(payload).hexdigest()
    download_video.fetch_video(root, "1-3", out, opener_for(payload, calls))
    assert len(calls) == 1
