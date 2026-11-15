"""The follow-up checks: thirds by activity, and who predicts whom."""
import numpy as np
import pandas as pd

from scripts import chosen_vs_random, why_not_mixed
from src import data, geometry, predict
from tests.conftest import make_cache, yaw_quaternion


def test_activity_is_the_mean_of_speed_and_exploration():
    style = pd.DataFrame({"head_speed": [1.0, -1.0], "exploration": [3.0, 0.0], "on_crowd": [9.0, 9.0]})
    assert np.allclose(why_not_mixed.activity(style), [2.0, -0.5])


def test_thirds_use_cut_points_from_the_pool_only():
    scores = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 100.0, -100.0])
    pool = np.arange(6)
    label = why_not_mixed.thirds(scores, pool)
    assert label[:6].tolist() == [0, 0, 1, 1, 2, 2]
    assert label[6] == 2 and label[7] == 0     # test viewers are labelled, but did not move the cut points


def camps_by_activity(n=24, seconds=12, hz=10):
    """Calm viewers (low score) all stare at one spot, active viewers at the opposite spot,
    middle viewers halfway. So here own kind really does predict own kind."""
    scores = np.linspace(-1, 1, n)
    yaw = np.where(scores < -1 / 3, -90.0, np.where(scores > 1 / 3, 90.0, 0.0))
    q = np.stack([yaw_quaternion(np.full(seconds * hz, y)) for y in yaw])
    w = geometry.tile_weights(q)
    vd = {"video": "1-1", "segments": predict.segment_weights(w, hz), "instant": predict.instant_weights(w, hz),
          "viewers": np.arange(1, n + 1)}
    return vd, scores


def test_cross_table_finds_own_kind_when_it_exists():
    vd, scores = camps_by_activity()
    cross = why_not_mixed.cross_one(vd, scores, n_trials=12, seed=0, budget=16, n_test=8)
    cell = cross.set_index(["test_viewers", "group_from"])["coverage"]
    for kind in why_not_mixed.THIRDS:
        own = cell.loc[(kind, kind)]
        others = [cell.loc[(kind, o)] for o in why_not_mixed.THIRDS if o != kind]
        assert own > 0.8 and max(others) < 0.5   # the window edge spills a little outside 16 tiles


def test_cross_summary_reports_own_minus_others():
    vd, scores = camps_by_activity()
    cross = pd.concat([why_not_mixed.cross_one({**vd, "video": v}, scores, 6, i, 16, 8) for i, v in enumerate(["1-1", "1-2", "2-1"])])
    cells, adv = why_not_mixed.cross_summary(cross, n_boot=300)
    assert len(cells) == 9 and (cells["videos"] == 3).all()
    assert (adv["own_minus_others"] > 0.4).all() and (adv["videos_above_zero"] == 3).all() and (adv["lo"] > 0).all()


def test_script_end_to_end(tmp_path):
    cache, out = tmp_path / "cache", tmp_path / "results"
    make_cache(cache, data.all_videos(), n_viewers=24, seconds=8)
    assert chosen_vs_random.main(["--cache", str(cache), "--out", str(out), "--check-only"]) == 0  # writes the style features
    code = why_not_mixed.main(["--cache", str(cache), "--out", str(out), "--trials", "3", "--ks", "2", "4", "--n-test", "8", "--jobs", "1"])
    assert code == 0
    note = (out / "why_not_mixed.md").read_text(encoding="utf-8")
    assert "### 12 of 72 tiles" in note and "### 24 of 72 tiles" in note and "| calm |" in note
    budget = pd.read_csv(out / "budget_check.csv")
    assert set(budget["budget"]) == {12, 24} and set(budget["arm"]) == {"mixed", "typical"}
    who = pd.read_csv(out / "who_predicts_whom.csv")
    assert set(who["kind"]) == {"cell", "own_minus_others"}
