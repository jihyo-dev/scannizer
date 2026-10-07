"""Generate sample_<preset>.pdf for each preset so the output can be inspected by eye.

Usage: python examples/make_samples.py [output_dir]
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as raw

from scannizer import scan
from scannizer.presets import PRESETS

LINES = [
    "SERVICE AGREEMENT",
    "",
    "This agreement is made on 6 October 2026 between the parties",
    "named below. Each party agrees to the terms set out in the",
    "following sections, which form an integral part of this document.",
    "",
    "1. Scope of work",
    "2. Fees and payment schedule",
    "3. Confidentiality",
    "4. Term and termination",
    "",
    "Signed: ______________________      Date: __________",
]


def _text(doc, page, text, x, y, size):
    font = raw.FPDFText_LoadStandardFont(doc, b"Helvetica")
    obj = raw.FPDFPageObj_CreateTextObj(doc, font, size)
    buf = (ctypes.c_ushort * (len(text) + 1))(*[ord(c) for c in text], 0)
    raw.FPDFText_SetText(obj, buf)
    raw.FPDFPageObj_Transform(obj, 1, 0, 0, 1, x, y)
    raw.FPDFPage_InsertObject(page, obj)


def _red_stamp(doc, page, x, y, r):
    path = raw.FPDFPageObj_CreateNewPath(x + r, y)
    k = 0.5523 * r
    raw.FPDFPath_BezierTo(path, x + r, y + k, x + k, y + r, x, y + r)
    raw.FPDFPath_BezierTo(path, x - k, y + r, x - r, y + k, x - r, y)
    raw.FPDFPath_BezierTo(path, x - r, y - k, x - k, y - r, x, y - r)
    raw.FPDFPath_BezierTo(path, x + k, y - r, x + r, y - k, x + r, y)
    raw.FPDFPath_Close(path)
    raw.FPDFPageObj_SetStrokeColor(path, 200, 30, 30, 255)
    raw.FPDFPageObj_SetStrokeWidth(path, 2.0)
    raw.FPDFPath_SetDrawMode(path, 0, 1)
    raw.FPDFPage_InsertObject(page, path)


def make_source(path: Path) -> Path:
    doc = pdfium.PdfDocument.new()
    for n in range(2):
        page = doc.new_page(595, 842)
        y = 760
        for i, line in enumerate(LINES):
            _text(doc, page, line, 72, y, 20 if i == 0 else 11)
            y -= 32 if i == 0 else 18
        _text(doc, page, f"Page {n + 1} of 2", 480, 40, 9)
        _red_stamp(doc, page, 470, 160, 28)
        raw.FPDFPage_GenerateContent(page)
    doc.save(path)
    doc.close()
    return path


def main() -> None:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "examples/output")
    out_dir.mkdir(parents=True, exist_ok=True)
    src = make_source(out_dir / "source.pdf")
    for name in PRESETS:
        scan(src, out_dir / f"sample_{name}.pdf", preset=name, seed=1)
        print("wrote", out_dir / f"sample_{name}.pdf")
    scan(src, out_dir / "sample_trifold_gray.pdf", fold="trifold", color="gray", seed=1)
    print("wrote", out_dir / "sample_trifold_gray.pdf")


if __name__ == "__main__":
    main()
