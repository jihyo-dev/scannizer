from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path

from .errors import ScannizerError
from .options import COLOR_MODES, FOLD_PATTERNS, ScanOptions
from .pipeline import scan
from .presets import PRESETS

_OVERRIDE_FIELDS = tuple(ScanOptions.__dataclass_fields__)


def default_output(src: Path) -> Path:
    return src.with_name(f"{src.stem}_scanned.pdf")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scannizer", description="Make a clean PDF look like it was scanned."
    )
    p.add_argument("input", type=Path, help="input PDF")
    p.add_argument("-o", "--output", type=Path, help="output PDF (default: <input>_scanned.pdf)")
    p.add_argument("--preset", choices=tuple(PRESETS), default="normal")
    p.add_argument("--seed", type=int, help="random seed for reproducible output")
    p.add_argument("--version", action="version", version=f"scannizer {version('scannizer')}")

    fx = p.add_argument_group("effect overrides (default: preset value)")
    fx.add_argument("--dpi", type=int, help="render resolution, 72-600")
    fx.add_argument("--color", choices=COLOR_MODES)
    fx.add_argument("--jpeg-quality", type=int, help="1-95")
    fx.add_argument("--skew", type=float, help="max tilt in degrees, 0-5")
    fx.add_argument("--fold", choices=FOLD_PATTERNS)
    for name in ("fold-strength", "noise", "paper", "edge-shadow", "unevenness"):
        fx.add_argument(f"--{name}", type=float, help="0-1")
    fx.add_argument("--blur", type=float, help="blur sigma in px at 200 DPI, 0-3")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    overrides = {
        name: getattr(args, name)
        for name in _OVERRIDE_FIELDS
        if getattr(args, name, None) is not None
    }
    output = args.output or default_output(args.input)
    try:
        scan(args.input, output, preset=args.preset, seed=args.seed, **overrides)
    except ValueError as exc:
        parser.error(str(exc))
    except ScannizerError as exc:
        print(f"scannizer: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
