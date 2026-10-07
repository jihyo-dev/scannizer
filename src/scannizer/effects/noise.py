from __future__ import annotations

import numpy as np


def apply_noise(img: np.ndarray, rng: np.random.Generator, strength: float) -> np.ndarray:
    """Sensor grain: shared luminance noise plus a weaker per-channel component."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    out = img.astype(np.float32)
    luma = rng.standard_normal(size=(h, w, 1), dtype=np.float32)
    luma *= 12.0 * strength
    out += luma
    del luma
    for c in range(img.shape[2]):  # one channel at a time keeps the peak at one extra plane
        chroma = rng.standard_normal(size=(h, w), dtype=np.float32)
        chroma *= 3.0 * strength
        out[..., c] += chroma
    np.rint(out, out=out)
    np.clip(out, 0, 255, out=out)
    return out.astype(np.uint8)
