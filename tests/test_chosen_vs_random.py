"""The chosen-versus-random script: the style gate, leakage, and outputs."""
import numpy as np
import pandas as pd

from scripts import baselines, chosen_vs_random
from src import data, evaluate, styles
from tests.conftest import make_cache


def z_features(cache, videos):
    return styles.standardise(pd.concat([styles.video_features(cache, v) for v in videos], ignore_index=True))


def test_style_check_sees_stable_styles(tmp_path):
    videos = data.all_videos()
    make_cache(tmp_path, videos, seconds=10)
    check = chosen_vs_random.style_check(z_features(tmp_path, videos))
    assert set(check) == {"odd vs even videos, all", "odd vs even videos, experiment 1",
                          "odd vs even videos, experiment 2", "experiment 1 vs experiment 2"}
    assert check["experiment 1 vs experiment 2"]["head_speed"] > 0.9
    assert chosen_vs_random.is_stable(check)


def test_style_check_fails_when_viewers_are_shuffled_between_videos(tmp_path):
    """Give every video a fresh random assignment of styles to viewers: nothing carries over."""
    videos = data.all_videos()
    rng = np.random.default_rng(0)
    for v in videos:
        kinds = list(rng.permutation(["still"] * 20 + ["follow"] * 10 + ["explore"] * 10))
        make_cache(tmp_path, [v], n_viewers=40, seconds=6, seed=int(rng.integers(1e6)), styles=kinds)
    check = chosen_vs_random.style_check(z_features(tmp_path, videos))
    assert not chosen_vs_random.is_stable(check)


def test_script_stops_before_outcomes_when_style_is_not_stable(tmp_path):
    cache, out = tmp_path / "cache", tmp_path / "results"
    rng = np.random.default_rng(1)
    for v in data.all_videos():
        kinds = list(rng.permutation(["still"] * 20 + ["follow"] * 10 + ["explore"] * 10))
        make_cache(cache, [v], n_viewers=40, seconds=6, seed=int(rng.integers(1e6)), styles=kinds)
    code = chosen_vs_random.main(["--cache", str(cache), "--out", str(out), "--jobs", "1"])
    assert code == 2
    assert (out / "style_check.md").exists() and not (out / "chosen_vs_random.csv").exists()
    assert "the script stops here" in (out / "style_check.md").read_text(encoding="utf-8")


def test_same_experiment_videos():
    assert chosen_vs_random.experiment_videos(2) == [f"2-{i}" for i in range(1, 10)]


def test_the_test_video_cannot_change_who_is_chosen(tmp_path):
    """Rewrite the test video's own features completely: the styles used for it must not move."""
    videos = ["1-1", "1-2", "1-3", "2-1"]
    make_cache(tmp_path, videos, seconds=10)
    z = z_features(tmp_path, videos)
    before = styles.style_for(z, "1-2")
    z2 = z.copy()
    z2.loc[z2["video"] == "1-2", list(styles.FEATURES)] = 123.0
    pd.testing.assert_frame_equal(styles.style_for(z2, "1-2"), before)
    pool = np.arange(8)
    g1 = styles.mixed_group(pool, 3, np.random.default_rng(0), before.to_numpy())
    g2 = styles.mixed_group(pool, 3, np.random.default_rng(0), styles.style_for(z2, "1-2").to_numpy())
    assert np.array_equal(g1, g2)


def test_script_end_to_end(tmp_path):
    cache, out = tmp_path / "cache", tmp_path / "results"
    make_cache(cache, data.all_videos(), seconds=12)
    base = ["--cache", str(cache), "--out", str(out), "--trials", "5", "--ks", "1", "2", "8", "--n-test", "4", "--jobs", "1"]
    assert baselines.main(base + ["--tuning-trials", "2"]) == 0      # writes the blend weights the script reads
    assert chosen_vs_random.main(base) == 0
    summary = pd.read_csv(out / "chosen_vs_random.csv")
    assert set(summary["arm"]) == {"none", "random", "mixed", "typical"}
    diff = pd.read_csv(out / "chosen_vs_random_diff.csv")
    assert set(diff["arm"]) == {"mixed", "typical"} and set(diff["metric"]) == set(evaluate.METRICS)
    assert (diff["lo"] <= diff["difference"]).all() and (diff["difference"] <= diff["hi"]).all()
    whole_pool = diff[diff["k"] == 8]                                  # 12 viewers, 4 test: the pool is 8
    assert np.allclose(whole_pool["difference"], 0.0)
    # the random arm is the same trials as in the baselines run
    b = pd.read_csv(out / "baselines_per_video.csv")
    c = pd.read_csv(out / "chosen_vs_random_per_video.csv")
    key = ["video", "k", "method"]
    merged = b[b["arm"] == "random"].merge(c[c["arm"] == "random"], on=key, suffixes=("_b", "_c"))
    assert len(merged) == 18 * 3 * 4 and np.allclose(merged["coverage_b"], merged["coverage_c"])
    for name in ("style_features.csv", "style_check.md", "chosen_vs_random.md", "chosen_vs_random.png",
                 "chosen_vs_random_same_experiment_diff.csv"):
        assert (out / name).exists()
    assert len(pd.read_csv(out / "style_features.csv")) == 18 * 12


def test_whole_pool_rows_are_found_and_left_out_of_the_tables():
    rows = []
    for k, value in ((4, -0.003), (32, 0.0)):
        for arm in ("mixed", "typical"):
            for metric in evaluate.METRICS:
                rows.append({"method": "crowd", "arm": arm, "k": k, "metric": metric, "difference": value,
                             "lo": value - (0.001 if k == 4 else 0), "hi": value + (0.001 if k == 4 else 0),
                             "videos_above_zero": 5 if k == 4 else 0, "videos": 18})
    diff = pd.DataFrame(rows)
    assert chosen_vs_random.whole_pool(diff) == {32}
    table = "\n".join(chosen_vs_random.diff_table(diff, "crowd", [4, 32]))
    assert "| 4 | mixed |" in table and "| 32 |" not in table
