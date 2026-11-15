"""From headset orientation to "which tiles of the video frame is this person seeing".

Axes are Unity's, as in the dataset paper: x right, y up, z forward. A headset
that has not been turned looks along +z.

The video frame is an equirectangular picture wrapped around the viewer. The
paper says the left edge of the frame sits on the +x axis and the picture wraps
round from there. So for a direction (x, y, z):

    across the frame   u = atan2(z, x) / 360 degrees, wrapped into [0, 1)
    down the frame     v = (90 - latitude) / 180, with latitude = asin(y)

The middle of the frame (u = 0.5) is the -x direction. Whether the frame runs
left-to-right or right-to-left around the viewer is not pinned down by the paper.
Coverage numbers do not depend on it, because a mirrored tile grid is the same
grid. It only matters when drawing over real video frames.

Tiles split the frame into `rows` x `cols` equal rectangles, numbered row by row
from the top-left. A viewport is what the headset shows: a square window `fov`
degrees wide and high, centred on the view direction and turned with the head,
including any tilt.
"""
from __future__ import annotations

import numpy as np

ROWS, COLS = 6, 12
FOV_DEG = 100.0
RAYS_PER_SIDE = 20  # even, so no ray sits exactly on the window's centre lines


def normalise(q: np.ndarray) -> np.ndarray:
    return q / np.linalg.norm(q, axis=-1, keepdims=True)


def rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vectors v by unit quaternions q = (x, y, z, w). Shapes broadcast."""
    u, w = q[..., :3], q[..., 3:4]
    c = np.cross(u, v)
    return v + 2 * w * c + 2 * np.cross(u, c)


def forward(q: np.ndarray) -> np.ndarray:
    """The direction the headset faces. Same as the formula in the dataset paper."""
    x, y, z, w = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([2 * x * z + 2 * y * w, 2 * y * z - 2 * x * w, 1 - 2 * x * x - 2 * y * y], axis=-1)


def frame_position(d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Direction -> (u, v) in the video frame, both in [0, 1). v = 0 is the top."""
    d = np.asarray(d, float)
    u = (np.arctan2(d[..., 2], d[..., 0]) / (2 * np.pi)) % 1.0
    lat = np.arcsin(np.clip(d[..., 1] / np.linalg.norm(d, axis=-1), -1.0, 1.0))
    v = np.clip(0.5 - lat / np.pi, 0.0, np.nextafter(1.0, 0.0))
    return u, v


def tile_index(d: np.ndarray, rows: int = ROWS, cols: int = COLS) -> np.ndarray:
    """Which tile a direction falls in, numbered row by row from the top-left."""
    u, v = frame_position(d)
    col = np.minimum((u * cols).astype(int), cols - 1)
    row = np.minimum((v * rows).astype(int), rows - 1)
    return row * cols + col


def viewport_rays(fov_deg: float = FOV_DEG, n: int = RAYS_PER_SIDE) -> np.ndarray:
    """n x n rays through the centres of an n x n grid on the headset's flat screen,
    for a headset that has not been turned. Each ray stands for an equal patch of
    screen, so counting rays measures share of what the viewer sees."""
    half = np.tan(np.radians(fov_deg) / 2)
    edge = (np.arange(n) + 0.5) / n * 2 * half - half
    a, b = np.meshgrid(edge, edge)
    rays = np.stack([a.ravel(), b.ravel(), np.ones(n * n)], axis=-1)
    return rays / np.linalg.norm(rays, axis=-1, keepdims=True)


def tile_weights(q: np.ndarray, rows: int = ROWS, cols: int = COLS, fov_deg: float = FOV_DEG,
                 n: int = RAYS_PER_SIDE, chunk: int = 4000) -> np.ndarray:
    """Share of the viewport that falls in each tile.

    q has shape (..., 4). The result has shape (..., rows * cols) and each row
    sums to 1. Rows where q is NaN (missing data) come back as NaN."""
    q = np.asarray(q, float)
    flat = q.reshape(-1, 4)
    out = np.full((len(flat), rows * cols), np.nan, dtype=np.float32)
    ok = np.flatnonzero(~np.isnan(flat).any(axis=1))
    rays = viewport_rays(fov_deg, n)
    for start in range(0, len(ok), chunk):
        idx = ok[start:start + chunk]
        world = rotate(flat[idx, None, :], rays[None, :, :])
        tiles = tile_index(world, rows, cols)
        counts = np.zeros((len(idx), rows * cols), dtype=np.float32)
        np.add.at(counts, (np.repeat(np.arange(len(idx)), rays.shape[0]), tiles.ravel()), 1.0)
        out[idx] = counts / rays.shape[0]
    return out.reshape(q.shape[:-1] + (rows * cols,))


def angle_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Angle in degrees between unit vectors."""
    return np.degrees(np.arccos(np.clip(np.sum(a * b, axis=-1), -1.0, 1.0)))
