from __future__ import annotations

import cv2
import numpy as np

REFERENCE_DPI = 200


def scale_px(value: float, dpi: int) -> float:
    """Convert a pixel-sized value defined at 200 DPI to the given DPI."""
    return value * dpi / REFERENCE_DPI


def smooth_noise(rng: np.random.Generator, shape: tuple[int, int], cells: int) -> np.ndarray:
    """Low-frequency noise in [-1, 1]: a cells×cells random grid upscaled with bicubic."""
    h, w = shape
    grid = rng.uniform(-1.0, 1.0, size=(cells, cells)).astype(np.float32)
    up = cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(up, -1.0, 1.0)


def to_float(img: np.ndarray) -> np.ndarray:
    return img.astype(np.float32) / 255.0


def to_uint8(img: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(img * 255.0), 0, 255).astype(np.uint8)
