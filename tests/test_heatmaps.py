"""The data summary and heatmap script."""
import numpy as np
import pandas as pd

from scripts import heatmaps
from src import geometry
from tests.conftest import yaw_quaternion


def looking(yaw_deg, viewers=3, ticks=20):
    return np.broadcast_to(yaw_quaternion(yaw_deg), (viewers, ticks, 4)).copy()


def test_on_screen_share_is_one_where_everyone_looks_and_zero_behind_them():
    grid = heatmaps.on_screen_share(looking(-90))  # the middle of the frame
    assert grid.shape == (36, 72)
    assert grid[18, 36] == 1.0 and grid[18, 0] == 0.0 and grid[0, 36] == 0.0
    assert set(np.unique(grid)) == {0.0, 1.0}
    assert 0.10 < grid.mean() < 0.20  # a 100 degree window is a modest part of the whole frame


def test_on_screen_share_averages_over_viewers_and_skips_missing_samples():
    q = np.concatenate([looking(-90, viewers=1), looking(90, viewers=1)])  # one looks at the middle, one at the seam
    q[1, :10] = np.nan
    grid = heatmaps.on_screen_share(q)
    assert np.isclose(grid[18, 36], 2 / 3) and np.isclose(grid[18, 0], 1 / 3)  # 4 present ticks vs 2 after thinning


def test_heatmap_columns_run_the_way_the_video_frame_does():
    grid = heatmaps.on_screen_share(looking(-90 + 60))  # 60 degrees towards lower u, which is the right of the picture
    assert grid[18, 36 + 12] == 1.0 and grid[18, 36 - 20] == 0.0


def test_tile_concentration():
    same_place = geometry.tile_weights(looking(-90))
    assert np.isclose(heatmaps.tile_concentration(same_place), 1.0, atol=1e-5)
    spread = geometry.tile_weights(np.stack([looking(a, viewers=1)[0] for a in range(0, 360, 30)]))
    assert 0.3 < heatmaps.tile_concentration(spread) < 0.6
    assert np.isclose(heatmaps.tile_concentration(spread, top=72), 1.0, atol=1e-5)


def test_summarise_reports_speed_and_missing_share():
    t = np.arange(40) / 10
    q = np.stack([yaw_quaternion(20 * t), yaw_quaternion(20 * t + 50), yaw_quaternion(np.zeros_like(t))])  # two turn at 20 deg/s, one sits still
    q[2, :4] = np.nan
    v = {"q": q, "weights": geometry.tile_weights(q), "hz": 10}
    row = heatmaps.summarise("1-1", v, {"Content": "Clip", "Category": "Sport"})
    assert row["seconds"] == 4.0 and row["viewers"] == 3
    assert np.isclose(row["missing_share"], 4 / 120)
    assert np.isclose(row["median_head_speed_deg_s"], 20.0, atol=0.5)
    assert row["share_within_30deg_of_horizon"] == 1.0


def test_script_writes_summary_and_figures(tiny_root, tmp_path):
    out = tmp_path / "results"
    code = heatmaps.main(["--root", str(tiny_root), "--cache", str(tmp_path / "cache"), "--out", str(out), "--viewers", "1", "2", "3", "4"])
    assert code == 0
    table = pd.read_csv(out / "data_summary.csv")
    assert len(table) == 18 and (table["viewers"] == 4).all() and (table["missing_share"] == 0).all()
    assert "| 2-9 |" in (out / "data_summary.md").read_text(encoding="utf-8")
    assert len(list((out / "heatmaps").glob("*.png"))) == 19
    assert (tmp_path / "cache" / "1-1.npz").exists()
