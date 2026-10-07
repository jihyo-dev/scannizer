from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from .assemble import write_pdf
from .effects.color import apply_color_mode
from .effects.fold import apply_fold
from .effects.geometry import apply_skew
from .effects.noise import apply_noise
from .effects.optics import apply_blur, apply_edge_shadow, apply_unevenness
from .effects.paper import apply_paper
from .errors import ScannizerError
from .options import ScanOptions
from .presets import get_preset
from .raster import open_pdf, render_page


def scan(
    src: str | os.PathLike,
    dst: str | os.PathLike,
    *,
    preset: str = "normal",
    seed: int | None = None,
    **overrides,
) -> None:
    """Render every page of `src`, apply scanner effects and write an image-only PDF to `dst`.

    `overrides` are ScanOptions field names and take precedence over the preset.
    """
    opts = get_preset(preset).replace(**overrides)
    src_path, dst_path = Path(src), Path(dst)
    if src_path.exists() and src_path.resolve() == dst_path.resolve():
        raise ScannizerError("output path is the same file as the input")
    if not dst_path.parent.is_dir():
        raise ScannizerError(f"output directory does not exist: {dst_path.parent}")

    doc = open_pdf(src_path)
    try:
        count = len(doc)
        if count == 0:
            raise ScannizerError(f"PDF has no pages: {src_path}")
        rngs = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(count)]

        def pages() -> Iterator[tuple[bytes, float, float]]:
            for index in range(count):
                width, height = doc.get_page_size(index)
                img = render_page(doc, index, opts.dpi)
                out = process_page(img, rngs[index], opts)
                yield encode_jpeg(out, opts.jpeg_quality), width, height

        _write_atomically(pages(), dst_path)
    finally:
        doc.close()


def process_page(img: np.ndarray, rng: np.random.Generator, opts: ScanOptions) -> np.ndarray:
    """Apply the effects in physical order: paper → fold → skew → optics → noise → colour."""
    img = apply_paper(img, rng, opts.paper, opts.dpi)
    img = apply_fold(img, rng, opts.fold, opts.fold_strength, opts.dpi)
    img = apply_skew(img, rng, opts.skew)
    img = apply_edge_shadow(img, rng, opts.edge_shadow, opts.dpi)
    img = apply_unevenness(img, rng, opts.unevenness)
    img = apply_blur(img, opts.blur, opts.dpi)
    img = apply_noise(img, rng, opts.noise)
    return apply_color_mode(img, opts.color)


def encode_jpeg(img: np.ndarray, quality: int) -> bytes:
    """JPEG-encode an RGB (H, W, 3) or grey (H, W) uint8 array."""
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise ScannizerError("JPEG encoding failed")
    return buf.tobytes()


def _write_atomically(pages: Iterator[tuple[bytes, float, float]], dst: Path) -> None:
    """Write to a temp file next to `dst`, then rename, so a crash never leaves a half PDF."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write_pdf(pages, tmp)
        os.replace(tmp, dst)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
