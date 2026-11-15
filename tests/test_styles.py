"""Style features and the three ways of picking a group."""
import numpy as np
import pandas as pd

from src import geometry, predict, styles
from tests.conftest import make_cache, yaw_quaternion

HZ = 10


def turning(deg_per_s, seconds=20, start=0.0):
    return yaw_quaternion(start + deg_per_s * np.arange(seconds * HZ) / HZ)


def test_head_speed_is_degrees_per_second():
    q = np.stack([turning(0), turning(15), turning(-40)])
    assert np.allclose(styles.head_speed(q, HZ), [0, 15, 40], atol=0.05)


def test_head_speed_ignores_jitter_that_goes_nowhere():
    wobble = yaw_quaternion(0.5 * (-1.0) ** np.arange(200))  # half a degree left and right, ten times a second
    assert styles.head_speed(wobble[None], HZ)[0] < 0.01


def test_exploration_is_zero_for_a_fixed_gaze_and_grows_with_tiles_visited():
    still = turning(0, start=-75)             # stays inside one tile
    two_tiles = yaw_quaternion(np.where(np.arange(200) < 100, -75.0, -105.0))
    full_turn = turning(18)                   # 360 degrees in 20 s: all 12 tiles of one row, equally
    e = styles.exploration(np.stack([still, two_tiles, full_turn]))
    assert np.isclose(e[0], 0.0) and np.isclose(e[1], 1.0) and np.isclose(e[2], np.log2(12), atol=0.02)


def test_exploration_skips_missing_samples():
    q = turning(0, start=-75)
    q[50:80] = np.nan
    assert np.isclose(styles.exploration(q[None])[0], 0.0)


def test_on_crowd_is_high_for_the_majority_and_zero_for_the_loner():
    q = np.stack([turning(0, start=-90)] * 5 + [turning(0, start=90)])
    seg = predict.segment_weights(geometry.tile_weights(q), HZ)
    share = styles.on_crowd(seg)
    assert np.allclose(share[:5], 1.0, atol=1e-5) and np.isclose(share[5], 0.0)


def test_on_crowd_leaves_the_viewer_out_of_their_own_crowd():
    """Two viewers in different places: each one's crowd is only the other, so both score zero."""
    q = np.stack([turning(0, start=-90), turning(0, start=90)])
    seg = predict.segment_weights(geometry.tile_weights(q), HZ)
    assert np.allclose(styles.on_crowd(seg), 0.0)


def test_standardise_is_per_video():
    f = pd.DataFrame({"video": ["a"] * 3 + ["b"] * 3, "viewer": [1, 2, 3] * 2,
                      "head_speed": [1.0, 2.0, 3.0, 10.0, 20.0, 30.0],
                      "exploration": [0.0, 1.0, 2.0, 5.0, 5.5, 6.0], "on_crowd": [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]})
    z = styles.standardise(f)
    assert np.allclose(z["head_speed"], [-1, 0, 1, -1, 0, 1])       # the fast video does not make everyone "fast"
    assert np.allclose(z.groupby("video")["on_crowd"].mean(), 0)
    assert f["head_speed"].iloc[0] == 1.0                           # the input is not changed


def features_table():
    rows = []
    for video, bump in (("1-1", 0.0), ("1-2", 1.0), ("2-1", 2.0)):
        for viewer in (1, 2, 3):
            rows.append({"video": video, "viewer": viewer, "head_speed": viewer + bump,
                         "exploration": -viewer, "on_crowd": 100.0 if video == "1-1" else 0.0})
    return pd.DataFrame(rows)


def test_style_never_uses_the_test_video():
    f = features_table()
    style = styles.style_for(f, "1-1")
    assert (style["on_crowd"] == 0).all()                           # the 100s live only in the test video
    assert np.allclose(style["head_speed"], [2.5, 3.5, 4.5])        # mean over 1-2 and 2-1
    changed = f.copy()
    changed.loc[changed["video"] == "1-1", "head_speed"] = 999.0
    pd.testing.assert_frame_equal(styles.style_for(changed, "1-1"), style)


def test_style_can_be_limited_to_the_same_experiment():
    f = features_table()
    style = styles.style_for(f, "1-1", allowed_videos=["1-1", "1-2"])
    assert np.allclose(style["head_speed"], [2.0, 3.0, 4.0])        # 1-2 only: the test video stays out even if listed


def test_mixed_group_takes_one_viewer_from_each_style_cluster():
    rng = np.random.default_rng(0)
    centres = np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]], float)
    style = np.concatenate([c + rng.normal(0, 0.3, size=(6, 3)) for c in centres])  # viewers 0-5, 6-11, 12-17
    pool = np.array([0, 1, 2, 3, 6, 7, 8, 12, 13, 14, 15])
    group = styles.mixed_group(pool, 3, np.random.default_rng(1), style)
    assert sorted(g // 6 for g in group) == [0, 1, 2] and set(group) <= set(pool)
    # nearest to the centre of its cluster
    for g in group:
        members = pool[pool // 6 == g // 6]
        centre = style[members].mean(axis=0)
        assert g == members[np.argmin(np.linalg.norm(style[members] - centre, axis=1))]


def test_mixed_group_of_the_whole_pool_is_the_pool():
    style = np.random.default_rng(0).normal(size=(10, 3))
    pool = np.array([9, 2, 5])
    assert np.array_equal(styles.mixed_group(pool, 3, np.random.default_rng(0), style), [2, 5, 9])


def test_typical_group_takes_the_viewers_most_on_the_crowd():
    style = np.zeros((6, 3))
    style[:, 2] = [0.1, 0.9, -0.5, 0.7, 0.3, 2.0]   # viewer 5 is not in the pool
    pool = np.array([0, 1, 2, 3, 4])
    assert np.array_equal(styles.typical_group(pool, 2, np.random.default_rng(0), style), [1, 3])
    assert np.array_equal(styles.typical_group(pool, 5, np.random.default_rng(0), style), pool)


def test_video_features_and_reliability_on_viewers_with_fixed_styles(tmp_path):
    videos = ["1-1", "1-2", "1-3", "1-4", "2-1", "2-2"]
    kinds = make_cache(tmp_path, videos, n_viewers=12, seconds=20)
    f = pd.concat([styles.video_features(tmp_path, v) for v in videos])
    assert len(f) == 6 * 12 and list(f.columns) == ["video", "viewer", "head_speed", "exploration", "on_crowd"]
    by_kind = f.assign(kind=np.tile(kinds, 6)).groupby("kind")[list(styles.FEATURES)].mean()
    assert by_kind.loc["explore", "head_speed"] > by_kind.loc["follow", "head_speed"] > by_kind.loc["still", "head_speed"]
    assert by_kind.loc["explore", "exploration"] > by_kind.loc["still", "exploration"]
    assert by_kind.loc["still", "on_crowd"] > by_kind.loc["explore", "on_crowd"]
    r = styles.split_half_reliability(styles.standardise(f), videos[::2], videos[1::2])
    assert r["head_speed"] > 0.9 and r["exploration"] > 0.7   # styles were built to be stable
