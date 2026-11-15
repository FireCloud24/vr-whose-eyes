"""Cleaning and resampling of session files."""
import numpy as np
import pandas as pd

from src import data, geometry, parse
from tests.conftest import write_session, yaw_quaternion


def frame(t, yaw=None):
    t = np.asarray(t, float)
    q = yaw_quaternion(np.zeros_like(t) if yaw is None else yaw)
    return pd.DataFrame({"t": t, "qx": q[:, 0], "qy": q[:, 1], "qz": q[:, 2], "qw": q[:, 3]})


def test_clean_cuts_leftover_rows_from_the_previous_video():
    df = parse.clean(frame([3.21, 3.21, 3.23, 0.0, 0.01, 0.02]))
    assert df["t"].tolist() == [0.0, 0.01, 0.02]


def test_clean_drops_backward_jitter_repeats_and_the_frozen_tail():
    df = parse.clean(frame([0.0, 0.01, 0.01, 0.03, 0.02, 0.04, 0.05, 0.05, 0.05]))
    assert df["t"].tolist() == [0.0, 0.01, 0.03, 0.04, 0.05]
    assert (np.diff(df["t"]) > 0).all()


def test_clean_keeps_a_small_backward_step_as_jitter_not_a_restart():
    df = parse.clean(frame([0.0, 0.5, 0.3, 0.6]))
    assert df["t"].tolist() == [0.0, 0.5, 0.6]


def test_resample_takes_the_nearest_row():
    t = np.arange(0, 2.0, 0.011)
    df = frame(t, yaw=t * 40)  # turning at 40 degrees a second
    q = parse.resample(df, n_ticks=20, hz=10)
    assert q.shape == (20, 4) and np.allclose(np.linalg.norm(q, axis=1), 1)
    yaw = np.degrees(2 * np.arctan2(q[:, 1], q[:, 3]))
    assert np.allclose(yaw, np.arange(20) / 10 * 40, atol=0.3)  # within half a row of the tick


def test_resample_marks_gaps_as_missing():
    t = np.concatenate([np.arange(0, 1.0, 0.011), np.arange(2.0, 3.0, 0.011)])  # one second lost
    q = parse.resample(frame(t), n_ticks=30, hz=10)
    missing = np.isnan(q).any(axis=1)
    assert not missing[:13].any() and missing[13:18].all() and not missing[18:].any()


def test_resample_renormalises_rounded_quaternions():
    df = frame([0.0, 0.1, 0.2])
    df[["qy", "qw"]] = [0.31, 0.95]  # three-decimal rounding leaves the norm a little off 1
    assert np.allclose(np.linalg.norm(parse.resample(df, 3, 10), axis=1), 1)


def test_load_video_puts_viewers_on_one_clock(tmp_path):
    root = tmp_path / "Formated_Data"
    start = pd.Timestamp("2016-11-17 02:00:00")
    write_session(root / "Experiment_1" / "1" / "video_0.csv", start, 3.0, yaw_deg=-90, stale_rows=5)
    write_session(root / "Experiment_1" / "2" / "video_0.csv", start, 3.5, yaw_deg=lambda t: 30 * t)
    v = parse.load_video(root, "1-1", viewers=(1, 2))
    assert v["q"].shape == (2, 29, 4)  # the shorter session ends just before 3.0 s
    assert not np.isnan(v["q"]).any()
    assert np.allclose(geometry.forward(v["q"][0]), [-1, 0, 0], atol=2e-3)       # stale rows did not leak in
    assert np.allclose(geometry.forward(v["q"][1, 0]), [0, 0, 1], atol=2e-3)
    assert geometry.forward(v["q"][1, -1])[0] > 0.9                              # turned about 84 degrees right


def test_cached_video_round_trips(tmp_path):
    root = tmp_path / "Formated_Data"
    for viewer in (1, 2):
        write_session(root / "Experiment_2" / str(viewer) / "video_3.csv", pd.Timestamp("2016-11-29 01:00:00"), 2.0, yaw_deg=10 * viewer)
    first = parse.cached_video(root, "2-4", cache=tmp_path / "cache", viewers=(1, 2))
    again = parse.cached_video(tmp_path / "nowhere", "2-4", cache=tmp_path / "cache", viewers=(1, 2))
    assert first["weights"].shape == (2, 19, 72) and np.allclose(first["weights"].sum(axis=-1), 1, atol=1e-5)
    assert np.array_equal(first["weights"], again["weights"]) and again["viewers"].tolist() == [1, 2]
    assert data.session_path(root, "2-4", 1).exists()
