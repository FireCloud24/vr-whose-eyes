"""Drawing what a viewer would see under a given set of high-quality tiles.

A video frame is an equirectangular image (height x width x 3, uint8). Tiles in
the chosen set keep full quality. Every other tile is shown as it would look at
a much lower bitrate, imitated here by shrinking and blowing the picture back up.
The viewer's window is then cut out of that picture with the same geometry the
metrics use, so the demo shows exactly what the coverage number measures.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from src import geometry


def degrade(frame: np.ndarray, factor: int = 24) -> np.ndarray:
    """A blocky low-quality copy of the frame: shrink by `factor`, then enlarge again."""
    h, w = frame.shape[:2]
    small = Image.fromarray(frame).resize((max(1, w // factor), max(1, h // factor)), Image.BILINEAR)
    return np.asarray(small.resize((w, h), Image.NEAREST))


def tile_mask_image(chosen: np.ndarray, height: int, width: int, mirror: bool = geometry.PICTURE_MIRRORED,
                    rows: int = geometry.ROWS, cols: int = geometry.COLS) -> np.ndarray:
    """(tiles,) boolean -> (height, width) boolean image, True where a pixel is in a chosen tile.
    With mirror=True, u = 0 is the right edge of the picture instead of the left.
    Real frames of this dataset are mirrored, which is the default."""
    grid = np.asarray(chosen, bool).reshape(rows, cols)
    if mirror:
        grid = grid[:, ::-1]
    r = np.minimum(np.arange(height) * rows // height, rows - 1)
    c = np.minimum(np.arange(width) * cols // width, cols - 1)
    return grid[r][:, c]


def compose(frame: np.ndarray, chosen: np.ndarray, mirror: bool = geometry.PICTURE_MIRRORED, factor: int = 24) -> np.ndarray:
    """The frame with chosen tiles sharp and all other tiles degraded."""
    mask = tile_mask_image(chosen, frame.shape[0], frame.shape[1], mirror)
    return np.where(mask[..., None], frame, degrade(frame, factor))


def viewport_pixels(q: np.ndarray, size: int, height: int, width: int, fov_deg: float = geometry.FOV_DEG,
                    mirror: bool = geometry.PICTURE_MIRRORED) -> tuple[np.ndarray, np.ndarray]:
    """For a size x size image of the viewer's window, the (row, column) of the frame
    pixel each window pixel shows. Row 0 of the window is the top of the view."""
    rays = geometry.viewport_rays(fov_deg, size).reshape(size, size, 3)[::-1]  # rays run bottom-up; images run top-down
    world = geometry.rotate(np.asarray(q, float), rays)
    u, v = geometry.frame_position(world)
    if mirror:
        u = 1.0 - u
    cols = np.minimum((u * width).astype(int), width - 1)
    rows = np.minimum((v * height).astype(int), height - 1)
    return rows, cols


def viewport_image(frame: np.ndarray, q: np.ndarray, size: int = 360, mirror: bool = geometry.PICTURE_MIRRORED) -> np.ndarray:
    """What the headset shows for orientation q: a size x size cut-out of the frame."""
    rows, cols = viewport_pixels(q, size, frame.shape[0], frame.shape[1], mirror=mirror)
    return frame[rows, cols]


def outline_viewport(frame: np.ndarray, q: np.ndarray, colour=(255, 255, 255), mirror: bool = geometry.PICTURE_MIRRORED, n: int = 240) -> np.ndarray:
    """The frame with the edge of the viewer's window drawn on it."""
    out = frame.copy()
    half = np.tan(np.radians(geometry.FOV_DEG) / 2)
    t = np.linspace(-half, half, n)
    edge = np.concatenate([np.stack([t, np.full(n, half)], 1), np.stack([t, np.full(n, -half)], 1),
                           np.stack([np.full(n, half), t], 1), np.stack([np.full(n, -half), t], 1)])
    rays = np.concatenate([edge, np.ones((len(edge), 1))], axis=1)
    rays /= np.linalg.norm(rays, axis=1, keepdims=True)
    u, v = geometry.frame_position(geometry.rotate(np.asarray(q, float), rays))
    if mirror:
        u = 1.0 - u
    h, w = frame.shape[:2]
    rows, cols = np.minimum((v * h).astype(int), h - 1), np.minimum((u * w).astype(int), w - 1)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            out[np.clip(rows + dr, 0, h - 1), (cols + dc) % w] = colour
    return out
