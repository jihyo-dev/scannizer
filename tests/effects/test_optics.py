import numpy as np
import pytest

from scannizer.effects.optics import apply_blur, apply_edge_shadow, apply_unevenness


@pytest.fixture
def white():
    return np.full((200, 160, 3), 255, dtype=np.uint8)


def test_identities(white):
    rng = np.random.default_rng(0)
    assert np.array_equal(apply_edge_shadow(white, rng, 0, 200), white)
    assert np.array_equal(apply_unevenness(white, rng, 0), white)
    assert np.array_equal(apply_blur(white, 0, 200), white)


def test_edge_shadow_darkens_edges_not_center():
    # Falloff is ~60 px at 200 DPI, so the page must be a few hundred px for a clean centre.
    page = np.full((600, 480, 3), 255, dtype=np.uint8)
    out = apply_edge_shadow(page, np.random.default_rng(1), 1.0, 200).astype(int)
    assert out[300, 240].min() > 245
    assert out[0, 240].max() < 245 or out[-1, 240].max() < 245
    assert out[300, 0].max() < 245 or out[300, -1].max() < 245


def test_edge_shadow_determinism_and_strength(white):
    a = apply_edge_shadow(white, np.random.default_rng(2), 0.5, 200)
    b = apply_edge_shadow(white, np.random.default_rng(2), 0.5, 200)
    strong = apply_edge_shadow(white, np.random.default_rng(2), 1.0, 200)
    assert np.array_equal(a, b)
    assert a.min() > strong.min()


def test_unevenness_is_smooth_gradient(white):
    out = apply_unevenness(white, np.random.default_rng(3), 1.0).astype(int)
    assert out.min() < 250  # some darkening happened
    assert np.abs(np.diff(out[..., 0], axis=1)).max() <= 2  # no hard steps
    assert np.array_equal(out, apply_unevenness(white, np.random.default_rng(3), 1.0))


def test_blur_spreads_a_line():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    img[25, :] = 255
    out = apply_blur(img, 1.0, 200)
    assert out.shape == img.shape and out.dtype == np.uint8
    assert out[24, 25, 0] > 0 and out[26, 25, 0] > 0
    assert out[25, 25, 0] < 255


def test_blur_scales_with_dpi():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    img[25, :] = 255
    low = apply_blur(img, 1.0, 100)
    high = apply_blur(img, 1.0, 400)
    assert high[22, 25, 0] > low[22, 25, 0]


def test_tiny_image_edge_shadow():
    tiny = np.full((3, 3, 3), 255, dtype=np.uint8)
    assert apply_edge_shadow(tiny, np.random.default_rng(0), 1.0, 600).shape == tiny.shape
