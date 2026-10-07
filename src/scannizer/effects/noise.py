from __future__ import annotations

import numpy as np


def apply_noise(img: np.ndarray, rng: np.random.Generator, strength: float) -> np.ndarray:
    """Sensor grain: shared luminance noise plus a weaker per-channel component."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    luma = rng.normal(0.0, 12.0 * strength, size=(h, w, 1)).astype(np.float32)
    chroma = rng.normal(0.0, 3.0 * strength, size=(h, w, img.shape[2])).astype(np.float32)
    out = img.astype(np.float32) + luma + chroma
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)
