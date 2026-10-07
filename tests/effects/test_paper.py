import numpy as np
import pytest

from scannizer.effects.paper import apply_paper


@pytest.fixture
def white():
    return np.full((120, 90, 3), 255, dtype=np.uint8)


def test_zero_strength_is_identity(white):
    out = apply_paper(white, np.random.default_rng(0), strength=0, dpi=200)
    assert np.array_equal(out, white)


def test_shape_dtype_and_determinism(white):
    a = apply_paper(white, np.random.default_rng(7), strength=0.5, dpi=200)
    b = apply_paper(white, np.random.default_rng(7), strength=0.5, dpi=200)
    c = apply_paper(white, np.random.default_rng(8), strength=0.5, dpi=200)
    assert a.shape == white.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def _diff_from_white(img):
    return np.abs(img.astype(int) - 255).mean()


def test_stronger_means_more_change(white):
    weak = apply_paper(white, np.random.default_rng(1), strength=0.2, dpi=200)
    strong = apply_paper(white, np.random.default_rng(1), strength=0.9, dpi=200)
    assert 0 < _diff_from_white(weak) < _diff_from_white(strong)


def test_tint_is_warm(white):
    out = apply_paper(white, np.random.default_rng(1), strength=1.0, dpi=200).astype(int)
    assert out[..., 0].mean() > out[..., 2].mean()  # R stays above B
    assert out.mean() > 215  # still reads as white paper


def test_black_text_stays_dark():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    out = apply_paper(img, np.random.default_rng(1), strength=1.0, dpi=200)
    assert out.max() < 20
