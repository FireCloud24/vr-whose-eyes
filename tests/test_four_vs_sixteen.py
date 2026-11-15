"""Four chosen against sixteen random: the comparison, the verdict words, the equivalent size."""
import numpy as np
import pandas as pd

from scripts import four_vs_sixteen as fvs
from src import evaluate

VIDEOS = ["1-1", "1-2", "1-3", "2-1", "2-2", "2-3"]
RANDOM_CURVE = {1: 0.60, 2: 0.64, 4: 0.68, 8: 0.72, 16: 0.76, 32: 0.80}  # +4 points per doubling


def table(mixed4=0.76, typical4=0.68, noise=0.0):
    rows = []
    for i, video in enumerate(VIDEOS):
        bump = 0.01 * i
        cells = [("random", k, v) for k, v in RANDOM_CURVE.items()]
        cells += [("mixed", 4, mixed4 + noise * (-1) ** i), ("typical", 4, typical4), ("mixed", 16, 0.76), ("typical", 16, 0.76)]
        for arm, k, cov in cells:
            for method in ("crowd", "blend_2", "blend_5"):
                rows.append({"video": video, "arm": arm, "k": k, "method": method, "coverage": cov + bump,
                             "coverage_worst10": cov + bump - 0.2, "poor_s_per_min": 60 * (1 - cov),
                             "poor_s_per_min_worst10": 90 * (1 - cov)})
    return pd.DataFrame(rows)


def test_comparison_is_four_minus_sixteen_random_per_video():
    d = fvs.comparison(table(mixed4=0.74), n_boot=300).set_index(["arm", "method", "metric"])
    assert np.isclose(d.loc[("mixed", "crowd", "coverage"), "difference"], -0.02)
    assert np.isclose(d.loc[("random", "crowd", "coverage"), "difference"], -0.08)
    assert np.isclose(d.loc[("typical", "blend_5", "coverage_worst10"), "difference"], -0.08)
    assert (d["k"] == 4).all() and (d["baseline"] == "random k=16").all() and (d["videos"] == 6).all()


def test_verdict_words_follow_the_interval():
    assert fvs.verdict(0.01, 0.03, True) == "four beat sixteen"
    assert fvs.verdict(-0.03, -0.01, True) == "sixteen beat four"
    assert fvs.verdict(-0.01, 0.02, True) == "no clear difference"
    assert fvs.verdict(-3.0, -1.0, False) == "four beat sixteen"     # fewer poor seconds is better
    assert fvs.verdict(1.0, 3.0, False) == "sixteen beat four"


def test_equivalent_random_k_reads_the_curve_backwards():
    assert np.isclose(fvs.equivalent_random_k(table(mixed4=0.76), "mixed", "crowd"), 16.0)
    assert np.isclose(fvs.equivalent_random_k(table(mixed4=0.74), "mixed", "crowd"), 2 ** 3.5)   # halfway between 8 and 16 on a log scale
    assert np.isclose(fvs.equivalent_random_k(table(typical4=0.68), "typical", "crowd"), 4.0)    # choosing added nothing
    assert np.isclose(fvs.equivalent_random_k(table(mixed4=0.95), "mixed", "crowd"), 32.0)       # off the top of the curve
    assert np.isclose(fvs.equivalent_random_k(table(mixed4=0.30), "mixed", "crowd"), 1.0)


def test_by_experiment_splits_the_videos():
    per = fvs.by_experiment(table(), n_boot=200)
    assert set(per["experiment"]) == {1, 2} and (per["videos"] == 3).all()


def test_script_writes_outputs_with_a_verdict_from_the_data(tmp_path):
    for mixed4, words in ((0.80, "four beat sixteen"), (0.70, "sixteen beat four"), (0.76, "no clear difference")):
        out = tmp_path / str(mixed4)
        out.mkdir()
        table(mixed4=mixed4, noise=0.01).to_csv(out / "chosen_vs_random_per_video.csv", index=False)
        assert fvs.main(["--out", str(out)]) == 0
        note = (out / "four_vs_sixteen.md").read_text(encoding="utf-8")
        mixed_row = next(line for line in note.splitlines() if line.startswith("| mixed |"))
        assert mixed_row.rstrip(" |").endswith(words)
        assert (out / "four_vs_sixteen.png").exists()
        csv = pd.read_csv(out / "four_vs_sixteen.csv")
        assert set(csv["experiment"].astype(str)) == {"both", "1", "2"} and set(csv["metric"]) == set(evaluate.METRICS)
