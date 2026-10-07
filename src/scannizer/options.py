from __future__ import annotations

import dataclasses
from dataclasses import dataclass

COLOR_MODES = ("color", "gray", "bw")
FOLD_PATTERNS = ("none", "half", "trifold")

_RANGES: dict[str, tuple[float, float]] = {
    "dpi": (72, 600),
    "jpeg_quality": (1, 95),
    "skew": (0.0, 5.0),
    "fold_strength": (0.0, 1.0),
    "noise": (0.0, 1.0),
    "paper": (0.0, 1.0),
    "edge_shadow": (0.0, 1.0),
    "unevenness": (0.0, 1.0),
    "blur": (0.0, 3.0),
}


@dataclass(frozen=True)
class ScanOptions:
    """All knobs for one scan() run. Pixel-sized values are defined at 200 DPI."""

    dpi: int = 200
    color: str = "color"
    jpeg_quality: int = 75
    skew: float = 0.7
    fold: str = "none"
    fold_strength: float = 0.5
    noise: float = 0.3
    paper: float = 0.25
    edge_shadow: float = 0.25
    unevenness: float = 0.2
    blur: float = 0.6

    def __post_init__(self) -> None:
        for name, (lo, hi) in _RANGES.items():
            value = getattr(self, name)
            if not lo <= value <= hi:
                raise ValueError(f"{name} must be between {lo} and {hi}, got {value!r}")
        if self.color not in COLOR_MODES:
            raise ValueError(f"color must be one of {COLOR_MODES}, got {self.color!r}")
        if self.fold not in FOLD_PATTERNS:
            raise ValueError(f"fold must be one of {FOLD_PATTERNS}, got {self.fold!r}")

    def replace(self, **overrides) -> ScanOptions:
        """Return a copy with some fields changed. Unknown names raise TypeError."""
        return dataclasses.replace(self, **overrides)
