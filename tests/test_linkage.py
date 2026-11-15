"""The viewer-ID checks, on synthetic recordings where the truth is known."""
import numpy as np
import pandas as pd

from scripts import check_ids
from src import data, linkage
from tests.conftest import make_dataset, write_session

VIEWERS = (1, 2, 3, 4)


def table(root):
    return linkage.session_table(root, viewers=VIEWERS)


def test_video_ids_and_paths():
    assert data.all_videos()[:2] == ["1-1", "1-2"] and data.all_videos()[-1] == "2-9" and len(data.all_videos()) == 18
    assert data.session_path("r", "2-9", 17).as_posix() == "r/Experiment_2/17/video_8.csv"


def test_read_raw_and_metadata(tiny_root):
    df = data.read_raw(tiny_root, "1-1", 2)
    assert list(df.columns) == ["timestamp", "t", "qx", "qy", "qz", "qw", "px", "py", "pz"]
    assert len(df) == 360 and df["timestamp"].dtype.kind == "M"
    meta = data.read_video_meta(tiny_root)
    assert meta["video"].tolist() == data.all_videos() and meta["duration_s"].tolist() == [4] * 18
    assert data.read_viewers(tiny_root)["viewer"].tolist() == [1, 2, 3, 4]


def test_clean_sittings_are_recognised(tiny_root):
    sessions = table(tiny_root)
    assert len(sessions) == 2 * 4 * 9
    sit = linkage.sittings(sessions)
    assert len(sit) == 8 and sit["one_sitting"].all() and (sit["videos"] == 9).all()
    assert linkage.overlapping_pairs(sessions) == 0


def test_a_video_recorded_again_later_breaks_the_sitting(tiny_root):
    write_session(tiny_root / "Experiment_1" / "3" / "video_0.csv", pd.Timestamp("2016-12-20 09:00:00"), 4.0)
    sit = linkage.sittings(table(tiny_root)).set_index(["experiment", "viewer"])
    assert not sit.loc[(1, 3), "one_sitting"] and not sit.loc[(1, 3), "in_play_order"]
    assert sit.drop(index=(1, 3))["one_sitting"].all()


def test_overlap_between_two_folders_is_counted(tiny_root):
    # Viewer 2's first video is rewritten to start in the middle of viewer 1's.
    write_session(tiny_root / "Experiment_1" / "2" / "video_0.csv", pd.Timestamp("2016-11-17 02:00:02"), 4.0)
    assert linkage.overlapping_pairs(table(tiny_root)) == 1


def test_arrival_order_correlation(tiny_root):
    sit = linkage.sittings(table(tiny_root))
    assert np.isclose(linkage.arrival_order_correlation(sit, 1), 1.0)   # recorded in folder order
    assert np.isclose(linkage.arrival_order_correlation(sit, 2), -1.0)  # recorded in reverse


def test_rank_correlation_ignores_scale():
    assert np.isclose(linkage.rank_correlation([1, 2, 3, 4], [10, 200, 3000, 40000]), 1.0)
    assert np.isclose(linkage.rank_correlation([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)


def test_permutation_p_is_small_for_a_real_link_and_large_for_none():
    rng = np.random.default_rng(1)
    x = rng.normal(size=40)
    assert linkage.permutation_p(x, x + rng.normal(scale=0.3, size=40), n_perm=2000) < 0.01
    assert linkage.permutation_p(x, rng.normal(size=40), n_perm=2000) > 0.05


def test_height_agrees_when_folders_are_people(tmp_path):
    viewers = tuple(range(1, 13))
    root = make_dataset(tmp_path / "linked", viewers=viewers, seconds=0.5)
    h = linkage.height_agreement(linkage.session_table(root, viewers=viewers), n_perm=2000)
    assert h["within_experiment_1_r"] > 0.95 and h["across_experiments_r"] > 0.95 and h["across_experiments_p"] < 0.01


def test_height_does_not_agree_when_experiment_2_is_other_people(tmp_path):
    """Scramble which person sits in which experiment-2 folder: the across-experiment
    agreement should vanish while the within-sitting agreement stays."""
    viewers = tuple(range(1, 13))
    root = make_dataset(tmp_path / "scrambled", viewers=viewers, seconds=0.5)
    perm = np.random.default_rng(3).permutation(viewers)
    truth = {v: 1.0 + 0.05 * v for v in viewers}
    for v, other in zip(viewers, perm):
        for i in range(9):
            write_session(root / "Experiment_2" / str(v) / f"video_{i}.csv",
                          pd.Timestamp("2016-11-29 01:00:00") + pd.Timedelta(3600 * int(v) + 30 * i, unit="s"), 0.5,
                          height=truth[int(other)])
    h = linkage.height_agreement(linkage.session_table(root, viewers=viewers), n_perm=2000)
    assert h["within_experiment_2_r"] > 0.95 and h["across_experiments_p"] > 0.05


def test_check_ids_script_writes_the_note(tiny_root, tmp_path, monkeypatch):
    monkeypatch.setattr(data, "VIEWERS", VIEWERS)
    monkeypatch.setattr(linkage.session_table, "__defaults__", (VIEWERS, None))
    out = tmp_path / "results"
    code = check_ids.main(["--root", str(tiny_root), "--out", str(out)])
    note = (out / "id_linkage.md").read_text(encoding="utf-8")
    assert code == 0
    assert "8 of 8 folders are one sitting" in note and "Within an experiment, a folder is one person." in note
    assert len(pd.read_csv(out / "sittings.csv")) == 8


def test_verdict_fails_when_sessions_overlap():
    counts = {1: {"folders": [1, 2], "files": 18}, 2: {"folders": [1, 2], "files": 18}, "demographics": [1, 2]}
    sit = pd.DataFrame({"one_sitting": [True] * 4})
    height = {"across_experiments_p": 0.001}
    assert check_ids.verdict(counts, sit, 0, {1: 1.0, 2: 0.1}, height)["within_experiment_link"]
    assert not check_ids.verdict(counts, sit, 3, {1: 1.0, 2: 0.1}, height)["within_experiment_link"]
    # Numbers that follow arrival order in both experiments give no support across them.
    assert not check_ids.verdict(counts, sit, 0, {1: 1.0, 2: 0.99}, height)["across_experiment_support"]
