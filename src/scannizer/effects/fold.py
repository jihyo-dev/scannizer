from __future__ import annotations

import math

import numpy as np

from .common import scale_px, to_float, to_uint8

_PATTERNS: dict[str, tuple[float, ...]] = {
    "none": (),
    "half": (0.5,),
    "trifold": (1 / 3, 2 / 3),
}


def fold_positions(pattern: str) -> tuple[float, ...]:
    """Fold line positions as fractions of page height."""
    return _PATTERNS[pattern]


def apply_fold(
    img: np.ndarray, rng: np.random.Generator, pattern: str, strength: float, dpi: int
) -> np.ndarray:
    """Draw horizontal fold creases: a dark band on one side, a light band on the other,
    plus a slightly different brightness for each folded panel."""
    positions = fold_positions(pattern)
    if not positions or strength <= 0:
        return img
    h, w = img.shape[:2]
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    shade = np.ones((h, w), dtype=np.float32)

    band = max(1.0, scale_px(6.0, dpi))
    for frac in positions:
        center = frac * h + rng.uniform(-0.01, 0.01) * h
        tilt = math.tan(math.radians(rng.uniform(-0.2, 0.2)))
        d = ys - (center + tilt * (xs - w / 2))  # signed distance from the crease
        dark = np.exp(-np.clip(-d, 0, None) / band) * (d <= 0)
        light = np.exp(-np.clip(d, 0, None) / (band * 1.5)) * (d > 0)
        shade *= 1.0 - strength * 0.35 * dark + strength * 0.06 * light

    # Each panel between creases gets its own slight brightness offset.
    edges = [0.0, *[p * h for p in positions], float(h)]
    for top, bottom in zip(edges[:-1], edges[1:], strict=True):
        offset = 1.0 + strength * rng.uniform(-0.03, 0.03)
        mask = (ys >= top) & (ys < bottom)
        shade *= np.where(mask, offset, 1.0).astype(np.float32)

    out = to_float(img) * shade[..., None]
    return to_uint8(out)
