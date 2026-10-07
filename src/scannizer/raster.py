from __future__ import annotations

from pathlib import Path

import numpy as np
import pypdfium2 as pdfium
import pypdfium2.raw as raw

from .errors import ScannizerError


def open_pdf(path: Path) -> pdfium.PdfDocument:
    """Open a PDF for reading, turning pdfium failures into ScannizerError."""
    path = Path(path)
    if not path.exists():
        raise ScannizerError(f"input file not found: {path}")
    if not path.is_file():
        raise ScannizerError(f"input is not a file: {path}")
    try:
        return pdfium.PdfDocument(path)
    except pdfium.PdfiumError as exc:
        if raw.FPDF_GetLastError() == raw.FPDF_ERR_PASSWORD:
            raise ScannizerError(f"encrypted PDFs are not supported: {path}") from exc
        raise ScannizerError(f"not a valid PDF: {path}") from exc


def render_page(doc: pdfium.PdfDocument, index: int, dpi: int) -> np.ndarray:
    """Render one page to an RGB uint8 array, honouring the page's /Rotate."""
    page = doc[index]
    try:
        bitmap = page.render(scale=dpi / 72, rev_byteorder=True)
        return np.array(bitmap.to_numpy()[..., :3], copy=True)
    finally:
        page.close()
