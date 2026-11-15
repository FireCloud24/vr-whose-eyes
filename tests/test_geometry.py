"""Orientation -> frame position -> tiles -> viewport, on orientations with known answers."""
import numpy as np
import pytest

from src import geometry
from tests.conftest import yaw_quaternion

IDENTITY = np.array([0.0, 0.0, 0.0, 1.0])


def axis_angle(axis, deg):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    half = np.radians(deg) / 2
    return np.append(axis * np.sin(half), np.cos(half))


def multiply(a, b):
    """Quaternion product a * b: apply b first, then a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


LOOK_UP = axis_angle([1, 0, 0], -90)       # pitch the nose up to the pole
LOOK_AT_FRAME_CENTRE = yaw_quaternion(-90)  # face -x, the middle of the frame
LOOK_AT_SEAM = yaw_quaternion(90)           # face +x, the left/right edge of the frame


def test_forward_matches_the_paper_and_general_rotation():
    assert np.allclose(geometry.forward(IDENTITY), [0, 0, 1])
    assert np.allclose(geometry.forward(yaw_quaternion(90)), [1, 0, 0], atol=1e-12)
    assert np.allclose(geometry.forward(LOOK_UP), [0, 1, 0], atol=1e-12)
    q = geometry.normalise(np.random.default_rng(0).normal(size=(50, 4)))
    assert np.allclose(geometry.forward(q), geometry.rotate(q, np.array([0.0, 0.0, 1.0])))
    assert np.allclose(np.linalg.norm(geometry.forward(q), axis=1), 1.0)


def test_frame_position_of_the_axes():
    u, v = geometry.frame_position(np.array([[1, 0, 0], [0, 0, 1], [-1, 0, 0], [0, 0, -1], [0, 1, 0], [0, -1, 0]]))
    assert np.allclose(u[:4], [0.0, 0.25, 0.5, 0.75])
    assert np.allclose(v[:4], 0.5) and v[4] == 0.0 and 0.999 < v[5] < 1.0


def test_tile_index_counts_row_by_row_from_the_top_left():
    def direction(lon_deg, lat_deg):
        lon, lat = np.radians(lon_deg), np.radians(lat_deg)
        return np.array([np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)])
    assert geometry.tile_index(direction(15, 75)) == 0            # top-left tile
    assert geometry.tile_index(direction(345, 75)) == 11          # top-right
    assert geometry.tile_index(direction(15, -75)) == 60          # bottom-left
    assert geometry.tile_index(direction(195, -15)) == 3 * 12 + 6  # just right of centre, just below the horizon
    assert geometry.tile_index(direction(359.9, 0.1)) == 2 * 12 + 11
    assert geometry.tile_index(direction(45, 10), rows=2, cols=4) == 0


def test_viewport_rays_span_the_field_of_view():
    rays = geometry.viewport_rays(100, 20)
    assert rays.shape == (400, 3) and np.allclose(np.linalg.norm(rays, axis=1), 1)
    assert np.allclose(rays.mean(axis=0)[:2], 0, atol=1e-12)
    centre_row = rays[np.abs(rays[:, 1]) < 0.06]
    widest = np.degrees(np.arctan2(centre_row[:, 0], centre_row[:, 2])).max()
    assert 45 < widest < 50  # outermost ray centre sits just inside the 50 degree edge


def test_weights_sum_to_one_everywhere():
    q = geometry.normalise(np.random.default_rng(1).normal(size=(200, 4)))
    w = geometry.tile_weights(q)
    assert w.shape == (200, 72) and np.allclose(w.sum(axis=1), 1, atol=1e-5) and (w >= 0).all()


def test_looking_at_the_frame_centre_fills_the_sixteen_middle_tiles():
    w = geometry.tile_weights(LOOK_AT_FRAME_CENTRE).reshape(6, 12)
    inside = np.zeros((6, 12), bool)
    inside[1:5, 4:8] = True
    assert np.isclose(w[inside].sum(), 1.0) and (w[~inside] == 0).all()
    assert np.allclose(w, w[:, ::-1], atol=1e-6) and np.allclose(w, w[::-1, :], atol=1e-6)  # symmetric window
    # The four tiles around the centre span 60 of the 100 degrees. On a flat screen
    # that is (tan 30 / tan 50) squared, about 23% of the picture.
    assert 0.2 < w[2:4, 5:7].sum() < 0.3


def test_viewport_wraps_across_the_seam():
    w = geometry.tile_weights(LOOK_AT_SEAM).reshape(6, 12)
    assert np.isclose(w[:, [10, 11, 0, 1]].sum(), 1.0)
    assert np.isclose(w[:, [10, 11]].sum(), w[:, [0, 1]].sum(), atol=1e-6)


def test_looking_straight_up_covers_the_top_rows_all_the_way_round():
    w = geometry.tile_weights(LOOK_UP).reshape(6, 12)
    assert np.isclose(w[:2].sum(), 1.0)
    assert (w[0] > 0).all()
    quarter_turns = w[:2].reshape(2, 4, 3).sum(axis=(0, 2))
    assert np.allclose(quarter_turns, 0.25, atol=1e-6)


def test_turning_the_head_one_tile_shifts_the_weights_one_column():
    a = geometry.tile_weights(yaw_quaternion(20)).reshape(6, 12)
    b = geometry.tile_weights(yaw_quaternion(20 - 30)).reshape(6, 12)  # yaw right lowers u, so -30 degrees is +1 column
    assert np.allclose(np.roll(a, 1, axis=1), b, atol=1e-6)


def test_mirrored_head_turn_gives_mirrored_weights():
    """Why the left/right ambiguity of the frame does not change coverage."""
    a = geometry.tile_weights(yaw_quaternion(-90 + 37)).reshape(6, 12)
    b = geometry.tile_weights(yaw_quaternion(-90 - 37)).reshape(6, 12)
    assert np.allclose(a, b[:, ::-1], atol=1e-6)


def test_tilting_the_head_a_quarter_turn_keeps_a_square_window():
    tilted = multiply(LOOK_AT_FRAME_CENTRE, axis_angle([0, 0, 1], 90))
    assert np.allclose(geometry.tile_weights(tilted), geometry.tile_weights(LOOK_AT_FRAME_CENTRE), atol=1e-6)
    tilted45 = multiply(LOOK_AT_FRAME_CENTRE, axis_angle([0, 0, 1], 45))
    assert not np.allclose(geometry.tile_weights(tilted45), geometry.tile_weights(LOOK_AT_FRAME_CENTRE), atol=1e-3)


def test_missing_orientation_gives_missing_weights():
    q = np.stack([IDENTITY, np.full(4, np.nan), IDENTITY]).reshape(1, 3, 4)
    w = geometry.tile_weights(q)
    assert w.shape == (1, 3, 72) and np.isnan(w[0, 1]).all() and np.allclose(w[0, 0], w[0, 2])


def test_a_finer_grid_adds_up_to_the_coarse_one():
    q = geometry.normalise(np.random.default_rng(2).normal(size=(20, 4)))
    coarse = geometry.tile_weights(q, 6, 12).reshape(20, 6, 12)
    fine = geometry.tile_weights(q, 18, 36).reshape(20, 6, 3, 12, 3).sum(axis=(2, 4))
    assert np.allclose(coarse, fine, atol=1e-6)


@pytest.mark.parametrize("a,b,deg", [([0, 0, 1], [0, 0, 1], 0), ([0, 0, 1], [1, 0, 0], 90), ([0, 0, 1], [0, 0, -1], 180)])
def test_angle_between(a, b, deg):
    assert np.isclose(geometry.angle_between(np.array(a, float), np.array(b, float)), deg)
