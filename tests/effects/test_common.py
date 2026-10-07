import numpy as np

from scannizer.effects.common import scale_px, smooth_noise, to_float, to_uint8


def test_scale_px():
    assert scale_px(10, 200) == 10
    assert scale_px(10, 100) == 5
    assert scale_px(10, 400) == 20


def test_smooth_noise_shape_range_and_determinism():
    a = smooth_noise(np.random.default_rng(1), (64, 48), cells=4)
    b = smooth_noise(np.random.default_rng(1), (64, 48), cells=4)
    c = smooth_noise(np.random.default_rng(2), (64, 48), cells=4)
    assert a.shape == (64, 48) and a.dtype == np.float32
    assert a.min() >= -1 and a.max() <= 1
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_smooth_noise_is_smooth():
    n = smooth_noise(np.random.default_rng(0), (200, 200), cells=3)
    assert np.abs(np.diff(n, axis=0)).max() < 0.1


def test_smooth_noise_tiny_image():
    assert smooth_noise(np.random.default_rng(0), (2, 3), cells=8).shape == (2, 3)


def test_float_uint8_roundtrip():
    img = np.array([[[0, 128, 255]]], dtype=np.uint8)
    f = to_float(img)
    assert f.dtype == np.float32 and f[0, 0, 2] == 1.0
    assert np.array_equal(to_uint8(f), img)
    assert to_uint8(np.array([[-0.5, 1.5]], dtype=np.float32)).tolist() == [[0, 255]]
