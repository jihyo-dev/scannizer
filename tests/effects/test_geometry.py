import numpy as np

from scannizer.effects.geometry import SCANNER_BED, apply_skew, sample_skew


def test_sample_skew_within_bounds():
    rng = np.random.default_rng(0)
    for _ in range(200):
        angle, dx, dy = sample_skew(rng, 1.5, width=1000, height=1400)
        assert -1.5 <= angle <= 1.5
        assert abs(dx) <= 5 and abs(dy) <= 7  # 0.5 % of each dimension


def test_zero_max_is_identity():
    img = np.random.default_rng(0).integers(0, 255, (80, 60, 3), dtype=np.uint8)
    assert np.array_equal(apply_skew(img, np.random.default_rng(0), 0.0), img)


def test_shape_dtype_determinism():
    img = np.full((200, 150, 3), 255, dtype=np.uint8)
    a = apply_skew(img, np.random.default_rng(1), 2.0)
    b = apply_skew(img, np.random.default_rng(1), 2.0)
    c = apply_skew(img, np.random.default_rng(2), 2.0)
    assert a.shape == img.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_exposed_corners_are_scanner_bed():
    img = np.zeros((300, 300, 3), dtype=np.uint8)  # black page makes corners obvious
    out = apply_skew(img, np.random.default_rng(3), 5.0)
    corners = [out[0, 0], out[0, -1], out[-1, 0], out[-1, -1]]
    assert any(tuple(c) == SCANNER_BED for c in corners)


def test_rotation_actually_rotates():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[100, :] = 255  # horizontal white line
    out = apply_skew(img, np.random.default_rng(4), 5.0)
    ys = np.flatnonzero(out[:, :, 0].max(axis=1) > 128)
    assert ys.max() - ys.min() > 3  # line now spans several rows
