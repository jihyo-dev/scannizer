from .options import ScanOptions

PRESETS: dict[str, ScanOptions] = {
    "light": ScanOptions(
        dpi=200,
        color="color",
        jpeg_quality=85,
        skew=0.3,
        fold="none",
        fold_strength=0.5,
        noise=0.15,
        paper=0.1,
        edge_shadow=0.1,
        unevenness=0.1,
        blur=0.3,
    ),
    "normal": ScanOptions(),
    "heavy": ScanOptions(
        dpi=150,
        color="gray",
        jpeg_quality=60,
        skew=1.5,
        fold="trifold",
        fold_strength=0.7,
        noise=0.55,
        paper=0.5,
        edge_shadow=0.5,
        unevenness=0.4,
        blur=1.0,
    ),
}


def get_preset(name: str) -> ScanOptions:
    try:
        return PRESETS[name]
    except KeyError:
        raise ValueError(f"unknown preset {name!r}; choose from {tuple(PRESETS)}") from None
