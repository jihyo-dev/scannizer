# scannizer

Make a clean PDF look like it was scanned.

scannizer rasterises each page, applies paper texture, fold creases, a slight
skew, scanner optics (edge shadow, uneven lighting, blur), sensor noise and
JPEG compression, then writes an image-only PDF — the same thing a real
scanner produces.

## Install

    pip install scannizer

Python 3.10+. Depends on pypdfium2, numpy and opencv-python-headless only.

## Command line

    scannizer input.pdf                       # → input_scanned.pdf
    scannizer input.pdf -o out.pdf --preset heavy --seed 42
    scannizer input.pdf --fold trifold --color gray --dpi 150

Presets: `light` (good scanner, fresh paper), `normal` (office copier, default),
`heavy` (old document, tired scanner). Any option can override the preset:

| Option | Meaning | Range |
|---|---|---|
| `--dpi` | render resolution | 72–600 |
| `--color` | `color`, `gray`, `bw` | |
| `--jpeg-quality` | JPEG quality | 1–95 |
| `--skew` | max tilt in degrees (random per page) | 0–5 |
| `--fold` | crease pattern: `none`, `half`, `trifold` | |
| `--fold-strength`, `--noise`, `--paper`, `--edge-shadow`, `--unevenness` | effect strength | 0–1 |
| `--blur` | blur sigma in px (at 200 DPI) | 0–3 |

`--seed N` makes the output reproducible; without it every run differs.

## Python

```python
from scannizer import scan

scan("in.pdf", "out.pdf")
scan("in.pdf", "out.pdf", preset="heavy", seed=42)
scan("in.pdf", "out.pdf", fold="trifold", color="gray")
```

`scan()` raises `scannizer.ScannizerError` for unreadable, encrypted or empty
input, and `ValueError` for out-of-range options.

## Development

    uv venv && uv pip install -e . --group dev
    python -m pytest
    python examples/make_samples.py   # visual check → examples/output/

## License

MIT
