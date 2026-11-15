"""The baselines script: budget rule, blend-weight tuning and outputs."""
import pandas as pd

from scripts import baselines
from src import data, evaluate
from tests.conftest import make_cache


def test_budget_rule_picks_the_smallest_budget_that_perfect_foresight_can_use():
    table = pd.DataFrame({"video": ["a"] * 3 + ["b"] * 3, "budget": [8, 16, 24] * 2,
                          "perfect_foresight_coverage": [0.6, 0.94, 0.99, 0.7, 0.97, 1.0]})
    assert baselines.pick_budget(table, rule=0.95) == 16     # mean at 16 is 0.955
    assert baselines.pick_budget(table, rule=0.96) == 24


def test_budget_table_is_perfect_at_the_full_frame_and_grows_with_budget(tmp_path):
    make_cache(tmp_path, ["1-1"])
    table = baselines.budget_table([evaluate.load_video(tmp_path, "1-1")]).set_index("budget")["perfect_foresight_coverage"]
    assert table.is_monotonic_increasing and table.loc[24] > 0.99 and table.loc[8] < 0.8


def test_weights_are_chosen_on_the_other_videos_only():
    rows = []
    for video, best in (("a", 0.9), ("b", 0.1), ("c", 0.1)):
        for w in (0.1, 0.5, 0.9):
            rows.append({"video": video, "k": 4, "horizon": 1, "own_weight": w, "coverage": 1.0 - (w - best) ** 2})
    used = baselines.leave_one_video_out_weights(pd.DataFrame(rows)).set_index("video")["own_weight"]
    assert used["a"] == 0.1                 # b and c agree on 0.1, whatever a itself prefers
    assert used["b"] == 0.5 and used["c"] == 0.5  # a wants 0.9 and the other wants 0.1: 0.5 is best on average
    assert baselines.weights_for(baselines.leave_one_video_out_weights(pd.DataFrame(rows)), "a") == {4: {1: 0.1}}


def test_script_end_to_end(tmp_path):
    cache, out = tmp_path / "cache", tmp_path / "results"
    make_cache(cache, data.all_videos())
    code = baselines.main(["--cache", str(cache), "--out", str(out), "--trials", "6", "--tuning-trials", "3",
                           "--ks", "1", "2", "4", "--n-test", "4", "--jobs", "1"])
    assert code == 0
    summary = pd.read_csv(out / "baselines.csv")
    assert set(summary["method"]) == {"own_1", "own_2", "own_5", "crowd", "blend_1", "blend_2", "blend_5"}
    assert (summary["videos"] == 18).all()
    assert ((summary["coverage_lo"] <= summary["coverage"]) & (summary["coverage"] <= summary["coverage_hi"])).all()
    assert summary["coverage"].between(0, 1).all() and summary["poor_s_per_min"].between(0, 60).all()
    own = summary[summary["k"] == 0].set_index("method")["coverage"]
    assert own["own_1"] > own["own_2"]      # nearer is easier
    weights = pd.read_csv(out / "blend_weights.csv")
    assert set(weights["kind"]) == {"candidate", "used"} and len(weights[weights["kind"] == "used"]) == 18 * 3 * 3
    assert len(pd.read_csv(out / "baselines_per_video.csv")) == 18 * (3 + 3 * 4)
    for name in ("budget.md", "baselines.md", "crowd_curve.png", "budget.csv"):
        assert (out / name).exists()
    assert "tiles**" in (out / "budget.md").read_text(encoding="utf-8")


def test_parallel_run_gives_the_same_numbers(tmp_path):
    cache = tmp_path / "cache"
    make_cache(cache, ["1-1", "1-2"])
    videos = [evaluate.load_video(cache, v) for v in ("1-1", "1-2")]
    one = baselines.weight_sweep(videos, (1, 2), 2, 0, 16, n_test=4, jobs=1)
    two = baselines.weight_sweep(videos, (1, 2), 2, 0, 16, n_test=4, jobs=2)
    pd.testing.assert_frame_equal(one, two)
