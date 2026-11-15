"""The demo: it must use the same splits and groups as the results, and its numbers must add up."""
import numpy as np
import pandas as pd
import pytest
from PIL import Image

from scripts import demo
from src import evaluate, metrics, predict, styles
from tests.conftest import make_cache

VIDEOS = ["1-1", "1-2", "1-3", "2-1"]


def test_parse_side():
    assert demo.parse_side("mixed:4") == ("mixed", 4) and demo.parse_side("random:16") == ("random", 16)
    with pytest.raises(ValueError):
        demo.parse_side("best:4")


def test_find_trial_follows_the_same_split_sequence_as_the_results():
    rng = np.random.default_rng([7, 0])
    splits = [evaluate.split_viewers(48, 16, rng) for _ in range(40)]
    pool, test, trial = demo.find_trial(48, viewer_row=5, seed=7)
    first = next(i for i, (_, t) in enumerate(splits) if 5 in t)
    assert trial == first and np.array_equal(pool, splits[first][0]) and 5 in test and 5 not in pool


def test_demo_groups_are_the_groups_the_trial_loop_used(tmp_path):
    """Recompute one trial's coverage by hand from the demo's groups and compare with run_video."""
    make_cache(tmp_path, VIDEOS, n_viewers=12, seconds=12)
    vd = evaluate.load_video(tmp_path, "1-2")
    seed, n_test = 3, 4
    trials = evaluate.run_video(vd, {"random": evaluate.random_group}, ks=(2,), n_trials=5, seed=seed, n_test=n_test)
    rng = np.random.default_rng([seed, 0])
    for trial in range(5):
        pool, test = evaluate.split_viewers(12, n_test, rng)
        group = demo.pick_groups([("random", 2)], pool, seed, trial, style=np.zeros((12, 3)))[("random", 2)]
        cov = evaluate.group_coverage(vd, group, test)["crowd"]
        expected = trials[(trials["trial"] == trial) & (trials["arm"] == "random")]["coverage"].iloc[0]
        assert np.isclose(metrics.mean_coverage(cov, axis=1).mean(), expected)


def test_build_makes_frames_and_facts(tmp_path):
    cache = tmp_path / "cache"
    make_cache(cache, VIDEOS, n_viewers=20, seconds=12)
    z = styles.standardise(pd.concat([styles.video_features(cache, v) for v in VIDEOS], ignore_index=True))
    frames = []
    for i in range(20):  # two seconds of made-up video frames
        path = tmp_path / f"{i:04d}.jpg"
        Image.fromarray(np.random.default_rng(i).integers(0, 255, size=(120, 240, 3), dtype=np.uint8)).save(path)
        frames.append(path)
    sides = [("mixed", 2), ("random", 4)]
    images, facts = demo.build("1-2", viewer=7, start=6, seconds=2, sides=sides, seed=1, cache=cache, frames=frames, z_features=z)
    assert len(images) == 20 and images[0].size == (2 * demo.VIEW + 8, demo.VIEW + demo.VIEW // 2 + 44)
    assert len(facts["group_mixed_2"].split()) == 2 and len(facts["group_random_4"].split()) == 4
    assert "7" not in facts["group_mixed_2"].split() + facts["group_random_4"].split()   # the viewer is never in a group
    # the clip number is the mean coverage of that viewer over those two seconds
    vd = evaluate.load_video(cache, "1-2")
    group = [int(g) - 1 for g in facts["group_random_4"].split()]
    cov = metrics.coverage(predict.choose_tiles(predict.crowd_scores(vd["segments"], group), 16), vd["segments"][6])
    assert np.isclose(facts["clip_coverage_random_4"], cov[6:8].mean())
    note = demo.render_note(facts, sides, "Made-up clip")
    assert "| 4 random viewers |" in note and "viewer 7" in note
    demo.save_gif(images, tmp_path / "demo.gif")
    gif = Image.open(tmp_path / "demo.gif")
    assert gif.n_frames == 10    # half the frames are kept
