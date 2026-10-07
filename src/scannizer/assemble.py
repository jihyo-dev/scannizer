from __future__ import annotations

import io
from collections.abc import Iterable
from pathlib import Path

import pypdfium2 as pdfium


def write_pdf(pages: Iterable[tuple[bytes, float, float]], dst: Path) -> None:
    """Build a PDF where each page is one full-bleed JPEG, embedded as-is (DCTDecode)."""
    doc = pdfium.PdfDocument.new()
    try:
        for jpeg, width, height in pages:
            page = doc.new_page(width, height)
            image = pdfium.PdfImage.new(doc)
            image.load_jpeg(io.BytesIO(jpeg), inline=True)
            image.set_matrix(pdfium.PdfMatrix().scale(width, height))
            page.insert_obj(image)
            page.gen_content()
            page.close()
        doc.save(dst)
    finally:
        doc.close()
