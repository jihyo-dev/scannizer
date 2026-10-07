import numpy as np
import pytest

from scannizer.effects.fold import apply_fold, fold_positions


@pytest.fixture
def white():
    return np.full((300, 200, 3), 255, dtype=np.uint8)


def test_fold_positions():
    assert fold_positions("none") == ()
    assert fold_positions("half") == (0.5,)
    assert fold_positions("trifold") == pytest.approx((1 / 3, 2 / 3))


def test_none_pattern_and_zero_strength_are_identity(white):
    assert np.array_equal(apply_fold(white, np.random.default_rng(0), "none", 0.8, 200), white)
    assert np.array_equal(apply_fold(white, np.random.default_rng(0), "half", 0.0, 200), white)


def test_shape_dtype_and_determinism(white):
    a = apply_fold(white, np.random.default_rng(3), "trifold", 0.6, 200)
    b = apply_fold(white, np.random.default_rng(3), "trifold", 0.6, 200)
    c = apply_fold(white, np.random.default_rng(4), "trifold", 0.6, 200)
    assert a.shape == white.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def _dark_rows(out):
    """Rows whose mean is clearly below the page's typical brightness."""
    row_mean = out.mean(axis=(1, 2))
    return np.flatnonzero(row_mean < np.median(row_mean) - 8)


def test_line_count_matches_pattern(white):
    for pattern, expected in [("half", 1), ("trifold", 2)]:
        out = apply_fold(white, np.random.default_rng(5), pattern, 0.8, 200)
        rows = _dark_rows(out)
        groups = 1 + int((np.diff(rows) > 3).sum()) if len(rows) else 0
        assert groups == expected, pattern


def test_lines_near_expected_positions(white):
    out = apply_fold(white, np.random.default_rng(5), "half", 1.0, 200)
    rows = _dark_rows(out)
    assert abs(rows.mean() - 150) < 300 * 0.02


def test_stronger_means_darker_line(white):
    weak = apply_fold(white, np.random.default_rng(1), "half", 0.2, 200)
    strong = apply_fold(white, np.random.default_rng(1), "half", 1.0, 200)
    assert weak.min() > strong.min()


def test_tiny_image_does_not_crash():
    tiny = np.full((5, 4, 3), 255, dtype=np.uint8)
    out = apply_fold(tiny, np.random.default_rng(0), "trifold", 1.0, 600)
    assert out.shape == tiny.shape
