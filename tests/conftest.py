from __future__ import annotations

import ctypes
from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def make_text_pdf(
    path: Path,
    sizes: list[tuple[float, float]] | None = None,
    text: str = "Hello scannizer",
    rotation: int = 0,
) -> Path:
    """Write a PDF whose pages each carry one line of Helvetica text."""
    doc = pdfium.PdfDocument.new()
    for width, height in sizes or [(595, 842)]:
        page = doc.new_page(width, height)
        font = raw.FPDFText_LoadStandardFont(doc, b"Helvetica")
        obj = raw.FPDFPageObj_CreateTextObj(doc, font, 24.0)
        buf = (ctypes.c_ushort * (len(text) + 1))(*[ord(c) for c in text], 0)
        raw.FPDFText_SetText(obj, buf)
        raw.FPDFPageObj_Transform(obj, 1, 0, 0, 1, width * 0.1, height * 0.8)
        raw.FPDFPage_InsertObject(page, obj)
        raw.FPDFPage_GenerateContent(page)
        if rotation:
            page.set_rotation(rotation)
    doc.save(path)
    doc.close()
    return path


def render_pdf_page(path: Path, index: int = 0, scale: float = 1.0) -> np.ndarray:
    doc = pdfium.PdfDocument(path)
    try:
        bitmap = doc[index].render(scale=scale, rev_byteorder=True)
        return np.array(bitmap.to_numpy()[..., :3], copy=True)
    finally:
        doc.close()


@pytest.fixture
def text_pdf(tmp_path):
    return make_text_pdf(tmp_path / "in.pdf")


@pytest.fixture
def encrypted_pdf():
    return FIXTURES / "encrypted.pdf"
