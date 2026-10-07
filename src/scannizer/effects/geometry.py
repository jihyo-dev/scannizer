from __future__ import annotations

import cv2
import numpy as np

SCANNER_BED = (236, 236, 236)  # light grey seen where the page does not cover the glass


def sample_skew(
    rng: np.random.Generator, max_degrees: float, width: int, height: int
) -> tuple[float, float, float]:
    """Random rotation angle (deg) and translation (px) for one page."""
    angle = float(rng.uniform(-max_degrees, max_degrees))
    dx = float(rng.uniform(-0.005, 0.005) * width)
    dy = float(rng.uniform(-0.005, 0.005) * height)
    return angle, dx, dy


def apply_skew(img: np.ndarray, rng: np.random.Generator, max_degrees: float) -> np.ndarray:
    """Rotate and shift the page slightly, keeping the canvas size."""
    if max_degrees <= 0:
        return img
    h, w = img.shape[:2]
    angle, dx, dy = sample_skew(rng, max_degrees, w, h)
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    matrix[:, 2] += (dx, dy)
    return cv2.warpAffine(
        img,
        matrix,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=SCANNER_BED,
    )
