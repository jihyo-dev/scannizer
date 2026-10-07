import numpy as np

from scannizer.effects.color import apply_color_mode


def _page():
    img = np.full((60, 80, 3), 240, dtype=np.uint8)
    img[20:40, 10:70] = (30, 30, 30)  # dark text block
    img[5:10, 5:10] = (200, 30, 30)  # red stamp
    return img


def test_color_is_identity():
    img = _page()
    assert apply_color_mode(img, "color") is img


def test_gray_is_single_channel_luminance():
    out = apply_color_mode(_page(), "gray")
    assert out.shape == (60, 80) and out.dtype == np.uint8
    assert out[0, 0] == 240 and out[30, 40] == 30
    assert 60 < out[7, 7] < 120  # red stamp becomes mid-dark grey


def test_bw_is_binary():
    out = apply_color_mode(_page(), "bw")
    assert out.shape == (60, 80) and out.dtype == np.uint8
    assert set(np.unique(out).tolist()) <= {0, 255}
    assert out[0, 0] == 255 and out[30, 40] == 0


def test_bw_blank_page_stays_white():
    blank = np.full((60, 80, 3), 235, dtype=np.uint8)
    blank[::7, ::5] = 225  # faint paper grain
    out = apply_color_mode(blank, "bw")
    assert (out == 255).mean() > 0.99
