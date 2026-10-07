import numpy as np
import pytest

from scannizer import ScannizerError
from scannizer.raster import open_pdf, render_page
from tests.conftest import make_text_pdf


def test_open_missing(tmp_path):
    with pytest.raises(ScannizerError, match="not found"):
        open_pdf(tmp_path / "nope.pdf")


def test_open_not_a_pdf(tmp_path):
    junk = tmp_path / "junk.pdf"
    junk.write_bytes(b"definitely not a pdf")
    with pytest.raises(ScannizerError, match="not a valid PDF"):
        open_pdf(junk)


def test_open_directory(tmp_path):
    with pytest.raises(ScannizerError):
        open_pdf(tmp_path)


def test_open_encrypted(encrypted_pdf):
    with pytest.raises(ScannizerError, match="encrypted"):
        open_pdf(encrypted_pdf)


def test_render_page_rgb_size_and_text(text_pdf):
    doc = open_pdf(text_pdf)
    try:
        img = render_page(doc, 0, dpi=72)
        assert img.shape == (842, 595, 3) and img.dtype == np.uint8
        assert img.mean() > 240  # mostly white
        assert img.min() < 50  # text is dark
        img2 = render_page(doc, 0, dpi=144)
        assert img2.shape == (1684, 1190, 3)
    finally:
        doc.close()


def test_render_respects_page_rotation(tmp_path):
    pdf = make_text_pdf(tmp_path / "rot.pdf", sizes=[(595, 842)], rotation=90)
    doc = open_pdf(pdf)
    try:
        assert doc.get_page_size(0) == pytest.approx((842, 595))
        assert render_page(doc, 0, dpi=72).shape == (595, 842, 3)
    finally:
        doc.close()
