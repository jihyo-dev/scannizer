from __future__ import annotations

import cv2
import numpy as np

# Fixed threshold: Otsu would split a blank page's grain into black and white.
_BW_THRESHOLD = 140


def apply_color_mode(img: np.ndarray, mode: str) -> np.ndarray:
    """Keep colour, convert to 8-bit grey, or binarise."""
    if mode == "color":
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    if mode == "gray":
        return gray
    _, bw = cv2.threshold(gray, _BW_THRESHOLD, 255, cv2.THRESH_BINARY)
    return bw
