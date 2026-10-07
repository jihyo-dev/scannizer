import cv2
import numpy as np
import pypdfium2 as pdfium

from scannizer.assemble import write_pdf
from tests.conftest import render_pdf_page


def _jpeg(img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    assert ok
    return buf.tobytes()


def test_write_pdf_embeds_jpegs_without_reencoding(tmp_path):
    colour = np.zeros((100, 50, 3), dtype=np.uint8)
    colour[:, :, 2] = 255  # BGR → red
    grey = np.full((50, 100), 90, dtype=np.uint8)
    pages = [(_jpeg(colour), 50.0, 100.0), (_jpeg(grey), 100.0, 50.0)]
    dst = tmp_path / "out.pdf"
    write_pdf(iter(pages), dst)

    doc = pdfium.PdfDocument(dst)
    assert len(doc) == 2
    assert doc.get_page_size(0) == (50.0, 100.0)
    assert doc.get_page_size(1) == (100.0, 50.0)
    assert doc[0].get_textpage().get_text_range() == ""
    img_obj = next(doc[0].get_objects())
    assert img_obj.get_filters() == ["DCTDecode"]
    doc.close()

    page0 = render_pdf_page(dst, 0)
    assert page0.shape == (100, 50, 3)
    assert page0[50, 25, 0] > 200 and page0[50, 25, 2] < 60  # red
    page1 = render_pdf_page(dst, 1)
    assert abs(int(page1[25, 50, 0]) - 90) < 5
