import pytest

from scannizer import ScannizerError, ScanOptions
from scannizer.options import COLOR_MODES, FOLD_PATTERNS
from scannizer.presets import PRESETS, get_preset


def test_defaults_equal_normal_preset():
    assert ScanOptions() == PRESETS["normal"]


@pytest.mark.parametrize(
    "field, value",
    [
        ("dpi", 71),
        ("dpi", 601),
        ("color", "rgb"),
        ("jpeg_quality", 0),
        ("jpeg_quality", 96),
        ("skew", -0.1),
        ("skew", 5.1),
        ("fold", "quarter"),
        ("fold_strength", 1.1),
        ("noise", -0.01),
        ("paper", 2),
        ("edge_shadow", 1.5),
        ("unevenness", -1),
        ("blur", 3.5),
    ],
)
def test_out_of_range_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        ScanOptions(**{field: value})


def test_boundaries_accepted():
    ScanOptions(dpi=72, jpeg_quality=1, skew=0, blur=0, noise=0)
    ScanOptions(dpi=600, jpeg_quality=95, skew=5, blur=3, noise=1)


def test_replace_overrides_and_validates():
    opts = get_preset("light").replace(fold="trifold", dpi=150)
    assert opts.fold == "trifold" and opts.dpi == 150
    assert opts.color == PRESETS["light"].color
    with pytest.raises(ValueError):
        get_preset("light").replace(dpi=10)
    with pytest.raises(TypeError):
        get_preset("light").replace(dpii=10)


def test_presets_and_enums():
    assert set(PRESETS) == {"light", "normal", "heavy"}
    assert PRESETS["heavy"].fold == "trifold" and PRESETS["heavy"].color == "gray"
    assert COLOR_MODES == ("color", "gray", "bw")
    assert FOLD_PATTERNS == ("none", "half", "trifold")
    with pytest.raises(ValueError, match="unknown preset"):
        get_preset("ultra")


def test_error_type():
    assert issubclass(ScannizerError, Exception)
