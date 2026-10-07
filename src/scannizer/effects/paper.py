from __future__ import annotations

import numpy as np

from .common import apply_shade, smooth_noise

# Warm tint applied to white at full strength (multiplicative per RGB channel).
_TINT = np.array([1.0, 0.985, 0.955], dtype=np.float32)


def apply_paper(img: np.ndarray, rng: np.random.Generator, strength: float, dpi: int) -> np.ndarray:
    """Multiply the page by a paper-fibre texture and shift whites slightly warm."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    cells = max(2, int(round(max(h, w) / (40 * dpi / 200))))
    # texture = 1 - strength * (0.03 * low + 0.012 * high), built in place on one buffer
    texture = rng.standard_normal(size=(h, w), dtype=np.float32)  # fibre grain
    texture *= 0.012 * strength
    low = smooth_noise(rng, (h, w), cells=cells)  # broad mottling
    low *= 0.03 * strength
    texture += low
    np.subtract(1.0, texture, out=texture)
    tint = 1.0 - strength * (1.0 - _TINT)
    return apply_shade(img, texture, tint)
