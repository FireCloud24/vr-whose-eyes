"""The experiment loop, on a made-up video with two camps of viewers."""
import numpy as np
import pandas as pd

from src import evaluate, geometry, predict
from tests.conftest import yaw_quaternion

CENTRE, SEAM = -90, 90  # yaw that faces the middle of the frame, and the opposite side


def camps_video(n_centre=8, n_seam=4, seconds=12, hz=10, mover=False):
    """Viewers 0..n_centre-1 stare at the middle of the frame, the rest at the seam.
    With mover=True the last viewer instead turns steadily."""
    ticks = seconds * hz
    yaws = [np.full(ticks, CENTRE)] * n_centre + [np.full(ticks, SEAM)] * n_seam
    if mover:
        yaws[-1] = CENTRE + 30.0 * np.arange(ticks) / hz
    weights = geometry.tile_weights(np.stack([yaw_quaternion(y) for y in yaws]))
    return {"video": "9-9", "segments": predict.segment_weights(weights, hz),
            "instant": predict.instant_weights(weights, hz), "viewers": np.arange(1, n_centre + n_seam + 1)}


def test_split_is_a_partition():
    pool, test = evaluate.split_viewers(48, 16, np.random.default_rng(0))
    assert len(pool) == 32 and len(test) == 16 and not set(pool) & set(test)
    assert sorted(set(pool) | set(test)) == list(range(48))
    other = evaluate.split_viewers(48, 16, np.random.default_rng(1))[1]
    assert not np.array_equal(test, other)


def test_random_group_comes_from_the_pool_without_repeats():
    pool = np.array([3, 5, 8, 13, 21])
    g = evaluate.random_group(pool, 3, np.random.default_rng(0))
    assert len(set(g)) == 3 and set(g) <= set(pool)
    assert np.array_equal(evaluate.random_group(pool, 5, np.random.default_rng(0)), pool)


def test_own_motion_is_perfect_for_someone_who_sits_still_and_worse_for_a_mover():
    vd = camps_video(mover=True)
    own = evaluate.own_motion_coverage(vd)
    assert set(own) == {1, 2, 5} and own[1].shape == (12, 12 - evaluate.SKIP)
    assert np.allclose(own[5][:11], 1.0, atol=1e-5)
    mover = [own[h][11].mean() for h in (1, 2, 5)]
    assert mover[0] > mover[1] > mover[2] and mover[0] < 1.0  # further ahead is harder


def test_a_group_serves_its_own_camp_and_fails_the_other():
    vd = camps_video()
    test = np.array([0, 1, 8, 9])  # two from each camp
    centre_group = evaluate.group_coverage(vd, np.array([2, 3]), test)["crowd"]
    assert np.allclose(centre_group[:2], 1.0, atol=1e-5) and np.allclose(centre_group[2:], 0.0)
    seam_group = evaluate.group_coverage(vd, np.array([10]), test)["crowd"]
    assert np.allclose(seam_group[:2], 0.0) and np.allclose(seam_group[2:], 1.0, atol=1e-5)


def test_a_mixed_group_splits_the_budget_between_camps():
    vd = camps_video()
    cov = evaluate.group_coverage(vd, np.array([2, 10]), np.array([0, 8]))["crowd"]
    assert (cov > 0.2).all() and (cov < 0.8).all()   # 16 tiles cannot hold two 16-tile windows
    assert np.isclose(cov[0].mean() + cov[1].mean(), 1.0, atol=0.15)


def test_blend_weight_one_is_own_motion_and_zero_is_the_crowd():
    vd = camps_video(mover=True)
    test, group = np.array([0, 11]), np.array([8, 9])
    own = evaluate.own_motion_coverage(vd)
    all_own = evaluate.group_coverage(vd, group, test, own_weights={1: 1.0, 5: 1.0})
    assert np.allclose(all_own["blend_1"], own[1][test]) and np.allclose(all_own["blend_5"], own[5][test])
    all_crowd = evaluate.group_coverage(vd, group, test, own_weights={2: 0.0})
    assert np.allclose(all_crowd["blend_2"], all_crowd["crowd"])


def test_score_reports_average_and_worst_tenth():
    cov = np.array([[1.0, 1.0, 1.0, 1.0], [0.4, 0.4, 0.6, 0.6], [0.0, 0.0, 0.0, 1.0]])
    s = evaluate.score(cov)
    assert np.isclose(s["coverage"], (1.0 + 0.5 + 0.25) / 3)
    assert np.isclose(s["coverage_worst10"], 0.25)            # a tenth of three viewers is part of the worst one
    assert np.isclose(s["poor_s_per_min"], (0 + 30 + 45) / 3)
    assert np.isclose(s["poor_s_per_min_worst10"], 45.0)


def always_centre(pool, k, rng):
    return np.sort(pool[pool < 8][:k])


def test_run_video_rows_pairing_and_determinism():
    vd = camps_video()
    arms = {"random": evaluate.random_group, "centre": always_centre}
    a = evaluate.run_video(vd, arms, ks=(1, 2), n_trials=6, seed=3, n_test=4)
    b = evaluate.run_video(vd, arms, ks=(1, 2), n_trials=6, seed=3, n_test=4)
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 6 * (3 + 2 * 2)                       # 3 own-motion rows, then 2 arms x 2 sizes
    assert set(a["method"]) == {"own_1", "own_2", "own_5", "crowd"} and (a["video"] == "9-9").all()
    own = a[a["arm"] == "none"]
    assert (own["k"] == 0).all() and np.allclose(own["coverage"], 1.0, atol=1e-5)
    centre = a[(a["arm"] == "centre") & (a["k"] == 1)]
    assert centre["coverage"].between(0, 1).all() and centre["coverage"].nunique() > 1  # depends on who is in the test set


def test_all_arms_coincide_when_the_group_is_the_whole_pool():
    vd = camps_video()
    arms = {"random": evaluate.random_group, "sorted": lambda pool, k, rng: pool[:k]}
    out = evaluate.run_video(vd, arms, ks=(8,), n_trials=5, seed=0, n_test=4)
    r = out[out["arm"] == "random"].reset_index(drop=True)
    s = out[out["arm"] == "sorted"].reset_index(drop=True)
    assert np.allclose(r["coverage"], s["coverage"]) and np.allclose(r["poor_s_per_min_worst10"], s["poor_s_per_min_worst10"])


def test_run_video_with_blends():
    vd = camps_video(mover=True)
    out = evaluate.run_video(vd, {"random": evaluate.random_group}, ks=(2,), n_trials=3, seed=0, n_test=4,
                             own_weights={2: {1: 0.8, 5: 0.3}})
    assert set(out["method"]) == {"own_1", "own_2", "own_5", "crowd", "blend_1", "blend_5"}


def test_per_video_and_across_videos():
    vd = camps_video()
    trials = pd.concat([evaluate.run_video({**vd, "video": name}, {"random": evaluate.random_group}, ks=(1, 4), n_trials=8, seed=i, n_test=4)
                        for i, name in enumerate(["1-1", "1-2", "2-1"])])
    table = evaluate.per_video(trials)
    assert len(table) == 3 * (3 + 2)
    summary = evaluate.across_videos(table, n_boot=500)
    assert len(summary) == 5 and (summary["videos"] == 3).all()
    row = summary[(summary["arm"] == "random") & (summary["k"] == 4)].iloc[0]
    assert row["coverage_lo"] <= row["coverage"] <= row["coverage_hi"]


def test_bootstrap_mean():
    mean, lo, hi = evaluate.bootstrap_mean([0.5] * 10, n_boot=200)
    assert mean == lo == hi == 0.5
    values = np.random.default_rng(0).normal(1.0, 1.0, size=18)
    mean, lo, hi = evaluate.bootstrap_mean(values, n_boot=4000)
    half_width = 1.96 * values.std(ddof=1) / np.sqrt(18)
    assert lo < mean < hi and np.isclose(hi - lo, 2 * half_width, rtol=0.2)


def test_adding_an_arm_or_a_size_does_not_change_the_others():
    vd = camps_video()
    alone = evaluate.run_video(vd, {"random": evaluate.random_group}, ks=(2,), n_trials=6, seed=5, n_test=4)
    more = evaluate.run_video(vd, {"centre": always_centre, "random": evaluate.random_group}, ks=(1, 2, 4), n_trials=6, seed=5, n_test=4)
    same = more[(more["arm"] == "random") & (more["k"] == 2)].reset_index(drop=True)
    pd.testing.assert_frame_equal(alone[alone["arm"] == "random"].reset_index(drop=True), same)


def per_video_table():
    rows = []
    for i, video in enumerate(["1-1", "1-2", "2-1", "2-2"]):
        for arm, k, cov in (("random", 4, 0.60), ("random", 16, 0.70), ("mixed", 4, 0.65 + 0.01 * i), ("mixed", 16, 0.70)):
            rows.append({"video": video, "arm": arm, "k": k, "method": "crowd", "coverage": cov + 0.02 * i,
                         "coverage_worst10": cov - 0.2, "poor_s_per_min": 10.0, "poor_s_per_min_worst10": 20.0})
        rows.append({"video": video, "arm": "none", "k": 0, "method": "own_1", "coverage": 0.8, "coverage_worst10": 0.6,
                     "poor_s_per_min": 5.0, "poor_s_per_min_worst10": 9.0})
    return pd.DataFrame(rows)


def test_paired_differences_at_the_same_k():
    d = evaluate.paired_differences(per_video_table(), n_boot=500)
    assert set(d["arm"]) == {"mixed"} and set(d["baseline"]) == {"random k=same"}
    row = d[(d["k"] == 4) & (d["metric"] == "coverage")].iloc[0]
    assert np.isclose(row["difference"], 0.05 + 0.01 * 1.5) and row["videos_above_zero"] == 4 and row["videos"] == 4
    assert row["lo"] <= row["difference"] <= row["hi"] and row["lo"] > 0
    tie = d[(d["k"] == 16) & (d["metric"] == "coverage")].iloc[0]
    assert np.isclose(tie["difference"], 0.0) and tie["videos_above_zero"] == 0


def test_paired_differences_against_a_fixed_size():
    d = evaluate.paired_differences(per_video_table(), baseline=("random", 16), n_boot=500)
    four = d[(d["arm"] == "mixed") & (d["k"] == 4) & (d["metric"] == "coverage")].iloc[0]
    assert np.isclose(four["difference"], -0.05 + 0.015) and four["baseline"] == "random k=16"
    assert not ((d["arm"] == "random") & (d["k"] == 16)).any()   # the baseline is not compared with itself
    assert ((d["arm"] == "random") & (d["k"] == 4)).any()
