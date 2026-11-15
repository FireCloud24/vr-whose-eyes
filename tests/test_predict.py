"""Segments, the three predictors and tile picking, on small cases worked by hand."""
import numpy as np

from src import geometry, predict
from tests.conftest import yaw_quaternion


def one_hot(tile, tiles=72):
    w = np.zeros(tiles, dtype=np.float32)
    w[tile] = 1.0
    return w


def test_segment_weights_average_each_second_and_skip_missing_ticks():
    w = np.zeros((1, 20, 4), dtype=np.float32)
    w[0, :10, 0] = 1.0           # first second: tile 0 throughout
    w[0, 10:15, 1] = 1.0         # second second: half on tile 1, half on tile 2
    w[0, 15:20, 2] = 1.0
    seg = predict.segment_weights(w, hz=10)
    assert seg.shape == (1, 2, 4)
    assert np.allclose(seg[0, 0], [1, 0, 0, 0]) and np.allclose(seg[0, 1], [0, 0.5, 0.5, 0])
    w[0, 15:20] = np.nan         # lose the second half: the average uses what is left
    assert np.allclose(predict.segment_weights(w, hz=10)[0, 1], [0, 1, 0, 0])
    w[0, 10:20] = np.nan         # lose the whole second
    assert np.isnan(predict.segment_weights(w, hz=10)[0, 1]).all()


def test_segment_weights_drop_a_trailing_part_second():
    assert predict.segment_weights(np.ones((2, 37, 3), dtype=np.float32), hz=10).shape == (2, 3, 3)


def test_instant_weights_take_the_segment_start_and_fill_gaps_from_the_past():
    w = np.zeros((1, 30, 3), dtype=np.float32)
    w[0, 0, 0] = w[0, 10, 1] = w[0, 20, 2] = 1.0
    inst = predict.instant_weights(w, hz=10)
    assert np.allclose(inst[0], np.eye(3))
    w[0, 10] = np.nan
    assert np.allclose(predict.instant_weights(w, hz=10)[0, 1], [1, 0, 0])


def test_own_motion_looks_back_by_the_horizon():
    inst = np.stack([one_hot(s, 6) for s in range(6)])[None]  # the viewer steps one tile a second
    own = predict.own_motion_scores(inst, horizon=2)
    assert np.isnan(own[0, :2]).all()
    assert np.array_equal(own[0, 2:], inst[0, :4])            # segment 2 is predicted from second 0


def test_crowd_scores_average_the_group_only():
    seg = np.stack([np.tile(one_hot(t, 4), (3, 1)) for t in (0, 1, 2, 3)])  # viewer i always on tile i
    assert np.allclose(predict.crowd_scores(seg, [0, 1])[0], [0.5, 0.5, 0, 0])
    assert np.allclose(predict.crowd_scores(seg, [3])[2], [0, 0, 0, 1])
    seg[1, 0] = np.nan  # viewer 1 has no data in segment 0
    assert np.allclose(predict.crowd_scores(seg, [0, 1])[0], [1, 0, 0, 0])
    assert np.allclose(predict.crowd_scores(seg, [0, 1])[1], [0.5, 0.5, 0, 0])


def test_blend_weights():
    own = one_hot(0, 3)[None, None]
    crowd = one_hot(2, 3)[None]
    assert np.allclose(predict.blend_scores(own, crowd, 0.75), [[[0.75, 0, 0.25]]])
    assert np.allclose(predict.blend_scores(own, crowd, 1.0), own) and np.allclose(predict.blend_scores(own, crowd, 0.0)[0], crowd)


def test_neighbour_sum_wraps_sideways_but_not_over_the_poles():
    left_edge = predict.neighbour_sum(one_hot(2 * 12 + 0)).reshape(6, 12)   # row 2, first column
    assert left_edge[2, 11] == 1 and left_edge[1, 11] == 1 and left_edge[3, 1] == 1 and left_edge[2, 0] == 0
    assert left_edge.sum() == 8
    top = predict.neighbour_sum(one_hot(5)).reshape(6, 12)                  # top row
    assert top.sum() == 5 and top[5].sum() == 0


def test_choose_tiles_takes_the_top_scores():
    scores = np.zeros(72)
    scores[[10, 20, 30]] = [0.5, 0.3, 0.2]
    mask = predict.choose_tiles(scores, budget=2)
    assert mask.sum() == 2 and mask[10] and mask[20]


def test_spare_tiles_pad_the_predicted_window():
    window = geometry.tile_weights(yaw_quaternion(-90))          # 16 tiles in the middle of the frame
    mask = predict.choose_tiles(window, budget=20).reshape(6, 12)
    assert mask[1:5, 4:8].all() and mask.sum() == 20
    extra = mask.copy()
    extra[1:5, 4:8] = False
    rows, cols = np.nonzero(extra)
    assert set(cols) <= {3, 8} or set(rows) <= {0, 5} or (set(cols) <= {3, 4, 5, 6, 7, 8} and set(rows) <= {0, 1, 2, 3, 4, 5})
    assert all((1 <= r <= 4 and c in (3, 8)) or (r in (0, 5) and 4 <= c <= 7) for r, c in zip(rows, cols))  # edge-adjacent, not corners or far away


def test_choose_tiles_is_deterministic_on_exact_ties_and_handles_batches():
    scores = np.zeros((2, 3, 72))
    a, b = predict.choose_tiles(scores, 16), predict.choose_tiles(scores, 16)
    assert np.array_equal(a, b) and (a.sum(axis=-1) == 16).all()


def test_no_information_chooses_nothing():
    scores = np.stack([np.full(72, np.nan), one_hot(5).astype(float)])
    mask = predict.choose_tiles(scores, 16)
    assert mask[0].sum() == 0 and mask[1].sum() == 16 and mask[1, 5]
