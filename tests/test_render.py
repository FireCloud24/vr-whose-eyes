"""The demo drawing code agrees with the geometry the metrics use."""
import numpy as np

from src import geometry, render
from tests.conftest import yaw_quaternion

H, W = 180, 360


def tile_coloured_frame():
    """A frame where every pixel's red channel is its tile number."""
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    rows = np.arange(H) * 6 // H
    cols = np.arange(W) * 12 // W
    frame[..., 0] = rows[:, None] * 12 + cols[None, :]
    return frame


def test_tile_mask_image_marks_the_right_rectangles():
    chosen = np.zeros(72, bool)
    chosen[0] = chosen[3 * 12 + 6] = True
    mask = render.tile_mask_image(chosen, H, W, mirror=False)
    assert mask[:30, :30].all() and mask[90:120, 180:210].all() and mask.sum() == 2 * 30 * 30
    mirrored = render.tile_mask_image(chosen, H, W, mirror=True)
    assert mirrored[:30, 330:].all() and mirrored[90:120, 150:180].all() and mirrored.sum() == 2 * 30 * 30


def test_compose_keeps_chosen_tiles_sharp_and_degrades_the_rest():
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 255, size=(H, W, 3), dtype=np.uint8)
    chosen = np.zeros(72, bool)
    chosen[10] = True
    out = render.compose(frame, chosen)
    mask = render.tile_mask_image(chosen, H, W)
    assert np.array_equal(out[mask], frame[mask])
    assert not np.array_equal(out[~mask], frame[~mask])
    assert np.array_equal(render.compose(frame, np.ones(72, bool)), frame)


def test_degrade_keeps_shape_and_loses_detail():
    rng = np.random.default_rng(1)
    frame = rng.integers(0, 255, size=(H, W, 3), dtype=np.uint8)
    low = render.degrade(frame, 12)
    assert low.shape == frame.shape and low.dtype == np.uint8
    assert len(np.unique(low[:12, :12, 0])) == 1          # one block is one colour


def test_window_shows_the_same_tiles_the_metric_counts():
    """Share of window pixels per tile, read off the picture, equals geometry.tile_weights."""
    frame = tile_coloured_frame()
    for q in (yaw_quaternion(-90), yaw_quaternion(37), geometry.normalise(np.array([0.2, -0.5, 0.1, 0.8]))):
        view = render.viewport_image(frame, q, size=20, mirror=False)
        seen = np.bincount(view[..., 0].ravel(), minlength=72) / 400
        assert np.allclose(seen, geometry.tile_weights(q), atol=1e-6)


def test_window_is_the_right_way_up_and_round():
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:H // 2] = 255                                   # sky above the horizon is white
    view = render.viewport_image(frame, yaw_quaternion(-90), size=40)
    assert view[:15].mean() > 250 and view[-15:].mean() < 5
    marker = np.zeros((H, W, 3), dtype=np.uint8)
    marker[:, 200:215] = 255                               # a stripe a little past the middle of the frame (u > 0.5)
    seen = render.viewport_image(marker, yaw_quaternion(-90), size=40, mirror=False)
    flipped = render.viewport_image(marker[:, ::-1], yaw_quaternion(-90), size=40, mirror=True)
    assert seen.sum() > 0 and np.array_equal(seen, flipped)  # mirroring the picture and the mapping together changes nothing


def test_outline_touches_only_the_window_edge():
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    out = render.outline_viewport(frame, yaw_quaternion(-90))
    drawn = out[..., 0] > 0
    assert drawn.any() and not drawn[85:95, 170:190].any()      # the centre of the window is untouched
    assert not drawn[:, :90].any() and not drawn[:, 270:].any()  # nothing behind the viewer
    cols = np.nonzero(drawn.any(axis=0))[0]
    assert 125 <= cols.min() <= 135 and 225 <= cols.max() <= 235  # 50 degrees either side of the centre


def test_real_frames_are_drawn_mirrored_by_default():
    assert geometry.PICTURE_MIRRORED
    chosen = np.zeros(72, bool)
    chosen[0] = True                                    # the tile at u = 0, top row
    assert render.tile_mask_image(chosen, H, W)[:30, 330:].all()   # sits at the right edge of the picture
