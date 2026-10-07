from __future__ import annotations

import math

import cv2
import numpy as np

from .common import scale_px, smooth_noise, to_float, to_uint8


def apply_edge_shadow(
    img: np.ndarray, rng: np.random.Generator, strength: float, dpi: int
) -> np.ndarray:
    """Darken the four page edges with an exponential falloff; each edge differs a little."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    width = max(1.0, scale_px(60.0, dpi))
    depth = 0.35 * strength
    shade = np.ones((h, w), dtype=np.float32)
    for dist in (ys, h - 1 - ys, xs, w - 1 - xs):
        edge_strength = depth * rng.uniform(0.3, 1.0)
        shade *= 1.0 - edge_strength * np.exp(-dist / width)
    return to_uint8(to_float(img) * shade[..., None])


def apply_unevenness(img: np.ndarray, rng: np.random.Generator, strength: float) -> np.ndarray:
    """Multiply by a gentle brightness map: a linear gradient in a random direction
    plus low-frequency mottling (lamp falloff, slightly lifted paper)."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    theta = rng.uniform(0, 2 * math.pi)
    ys = (np.arange(h, dtype=np.float32) / max(h - 1, 1) - 0.5)[:, None]
    xs = (np.arange(w, dtype=np.float32) / max(w - 1, 1) - 0.5)[None, :]
    gradient = xs * math.cos(theta) + ys * math.sin(theta)  # [-0.7, 0.7]
    mottle = smooth_noise(rng, (h, w), cells=4)
    shade = 1.0 - strength * 0.12 * (1.0 + 0.8 * gradient + 0.5 * mottle) / 2.3
    return to_uint8(to_float(img) * shade[..., None])


def apply_blur(img: np.ndarray, sigma: float, dpi: int) -> np.ndarray:
    """Gaussian blur; sigma is given in pixels at 200 DPI."""
    if sigma <= 0:
        return img
    s = scale_px(sigma, dpi)
    return cv2.GaussianBlur(img, (0, 0), sigmaX=s, sigmaY=s)
