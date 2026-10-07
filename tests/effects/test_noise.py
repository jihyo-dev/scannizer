import numpy as np

from scannizer.effects.noise import apply_noise


def test_zero_is_identity():
    img = np.full((40, 40, 3), 200, dtype=np.uint8)
    assert np.array_equal(apply_noise(img, np.random.default_rng(0), 0), img)


def test_shape_dtype_determinism():
    img = np.full((40, 40, 3), 200, dtype=np.uint8)
    a = apply_noise(img, np.random.default_rng(1), 0.5)
    b = apply_noise(img, np.random.default_rng(1), 0.5)
    c = apply_noise(img, np.random.default_rng(2), 0.5)
    assert a.shape == img.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_strength_controls_spread():
    img = np.full((200, 200, 3), 128, dtype=np.uint8)
    weak = apply_noise(img, np.random.default_rng(1), 0.2).astype(float)
    strong = apply_noise(img, np.random.default_rng(1), 1.0).astype(float)
    assert 0 < weak.std() < strong.std()
    assert abs(strong.mean() - 128) < 1.5  # zero-mean noise
    assert strong.std() < 20  # still readable


def test_mostly_luminance_noise():
    img = np.full((200, 200, 3), 128, dtype=np.uint8)
    out = apply_noise(img, np.random.default_rng(1), 1.0).astype(float)
    channel_spread = (out.max(axis=2) - out.min(axis=2)).mean()
    luma_spread = out.mean(axis=2).std()
    assert channel_spread < luma_spread
