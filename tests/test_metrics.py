"""Coverage, poor seconds and the worst-10% average."""
import numpy as np
import pytest

from src import metrics


def test_coverage_is_the_share_of_the_window_on_chosen_tiles():
    actual = np.array([[0.5, 0.3, 0.2, 0.0], [0.0, 0.0, 0.4, 0.6]])
    chosen = np.array([[True, True, False, False], [True, True, False, False]])
    assert np.allclose(metrics.coverage(chosen, actual), [0.8, 0.0])
    assert np.allclose(metrics.coverage(np.ones((2, 4), bool), actual), 1.0)


def test_coverage_is_unknown_when_the_window_is_unknown():
    actual = np.array([[np.nan] * 3, [0.2, 0.3, 0.5]])
    cov = metrics.coverage(np.array([[True, False, False]] * 2), actual)
    assert np.isnan(cov[0]) and np.isclose(cov[1], 0.2)


def test_coverage_broadcasts_one_choice_over_many_viewers():
    actual = np.array([[[1.0, 0.0]], [[0.0, 1.0]], [[0.5, 0.5]]])  # 3 viewers, 1 segment, 2 tiles
    chosen = np.array([[True, False]])                            # 1 segment
    assert np.allclose(metrics.coverage(chosen[None], actual), [[1.0], [0.0], [0.5]])


def test_mean_coverage_ignores_unknown_segments():
    assert np.isclose(metrics.mean_coverage(np.array([1.0, np.nan, 0.5])), 0.75)


def test_poor_seconds_per_minute():
    cov = np.array([0.9, 0.4, 0.49, 0.5, 0.8, 0.2])  # 3 of 6 one-second segments are under a half
    assert np.isclose(metrics.poor_seconds_per_minute(cov), 30.0)
    assert np.isclose(metrics.poor_seconds_per_minute(cov, below=0.3), 10.0)
    with_gap = np.array([0.9, np.nan, 0.1, 0.1])     # unknown segments are not counted either way
    assert np.isclose(metrics.poor_seconds_per_minute(with_gap), 40.0)
    assert np.allclose(metrics.poor_seconds_per_minute(np.array([[0.1, 0.9], [0.9, 0.9]])), [30.0, 0.0])


def test_tail_mean_with_whole_and_part_viewers():
    twenty = np.arange(1, 21) / 20                       # 0.05 ... 1.0
    assert np.isclose(metrics.tail_mean(twenty, 0.10), (0.05 + 0.10) / 2)            # worst 2 of 20
    assert np.isclose(metrics.tail_mean(twenty, 0.10, worst="high"), (1.0 + 0.95) / 2)
    sixteen = np.arange(16.0)
    # a tenth of 16 is 1.6 viewers: all of the worst and 0.6 of the next
    assert np.isclose(metrics.tail_mean(sixteen, 0.10), (0 * 1.0 + 1 * 0.6) / 1.6)
    assert np.isclose(metrics.tail_mean(sixteen, 0.10, worst="high"), (15 * 1.0 + 14 * 0.6) / 1.6)


def test_tail_mean_edge_cases():
    assert metrics.tail_mean([0.3, 0.7], 1.0) == pytest.approx(0.5)      # the whole group
    assert metrics.tail_mean([0.3, 0.7, np.nan], 0.5) == pytest.approx(0.3)  # NaN viewers are left out
    assert metrics.tail_mean([0.4], 0.1) == pytest.approx(0.4)           # less than one viewer still means that viewer


def test_tail_mean_never_beats_the_plain_mean():
    values = np.random.default_rng(0).uniform(size=40)
    assert metrics.tail_mean(values, 0.1) <= values.mean() <= metrics.tail_mean(values, 0.1, worst="high")
