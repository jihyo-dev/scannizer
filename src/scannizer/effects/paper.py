from __future__ import annotations

import numpy as np

from .common import smooth_noise, to_float, to_uint8

# Warm tint applied to white at full strength (multiplicative per RGB channel).
_TINT = np.array([1.0, 0.985, 0.955], dtype=np.float32)


def apply_paper(img: np.ndarray, rng: np.random.Generator, strength: float, dpi: int) -> np.ndarray:
    """Multiply the page by a paper-fibre texture and shift whites slightly warm."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    cells = max(2, int(round(max(h, w) / (40 * dpi / 200))))
    low = smooth_noise(rng, (h, w), cells=cells)  # broad mottling
    high = rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)  # fibre grain
    texture = 1.0 - strength * (0.03 * low + 0.012 * high)
    tint = 1.0 - strength * (1.0 - _TINT)
    out = to_float(img) * texture[..., None] * tint
    return to_uint8(out)
