import numpy as np
import pypdfium2 as pdfium
import pytest

from scannizer import ScannizerError, ScanOptions, scan
from scannizer.pipeline import encode_jpeg, process_page
from tests.conftest import make_text_pdf, render_pdf_page


def _page_sizes(path):
    doc = pdfium.PdfDocument(path)
    try:
        return [doc.get_page_size(i) for i in range(len(doc))]
    finally:
        doc.close()


def test_process_page_shapes():
    img = np.full((200, 150, 3), 255, dtype=np.uint8)
    rng = np.random.default_rng(0)
    assert process_page(img, rng, ScanOptions()).shape == (200, 150, 3)
    assert process_page(img, rng, ScanOptions(color="gray")).shape == (200, 150)
    bw = process_page(img, rng, ScanOptions(color="bw"))
    assert set(np.unique(bw).tolist()) <= {0, 255}


def test_process_page_all_effects_off_is_identity():
    img = np.random.default_rng(0).integers(0, 255, (60, 40, 3), dtype=np.uint8)
    opts = ScanOptions(skew=0, fold="none", noise=0, paper=0, edge_shadow=0, unevenness=0, blur=0)
    assert np.array_equal(process_page(img, np.random.default_rng(0), opts), img)


def test_encode_jpeg_roundtrip():
    img = np.full((20, 30, 3), (200, 50, 50), dtype=np.uint8)
    data = encode_jpeg(img, 90)
    assert data[:2] == b"\xff\xd8"
    grey = encode_jpeg(np.full((20, 30), 100, dtype=np.uint8), 90)
    assert grey[:2] == b"\xff\xd8"


def test_scan_end_to_end(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf", sizes=[(595, 842), (842, 595), (300, 300)])
    dst = tmp_path / "out.pdf"
    scan(src, dst, seed=1, dpi=72)
    assert _page_sizes(dst) == [(595, 842), (842, 595), (300, 300)]
    doc = pdfium.PdfDocument(dst)
    assert all(doc[i].get_textpage().get_text_range() == "" for i in range(3))
    doc.close()
    page = render_pdf_page(dst, 0)
    assert page.shape == (842, 595, 3)
    assert page.min() < 80 and page.mean() > 180  # text survived, page still light


def test_scan_is_reproducible_with_seed(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf")
    scan(src, tmp_path / "a.pdf", seed=42, dpi=72)
    scan(src, tmp_path / "b.pdf", seed=42, dpi=72)
    scan(src, tmp_path / "c.pdf", seed=43, dpi=72)
    a, b, c = (render_pdf_page(tmp_path / f"{n}.pdf") for n in "abc")
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_scan_pages_differ_from_each_other(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf", sizes=[(300, 300), (300, 300)])
    scan(src, tmp_path / "out.pdf", seed=1, dpi=72, preset="heavy")
    assert not np.array_equal(
        render_pdf_page(tmp_path / "out.pdf", 0), render_pdf_page(tmp_path / "out.pdf", 1)
    )


def test_scan_accepts_str_paths_and_presets(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf")
    scan(str(src), str(tmp_path / "out.pdf"), preset="light", dpi=72)
    assert (tmp_path / "out.pdf").exists()


def test_scan_rejects_bad_options(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf")
    with pytest.raises(ValueError):
        scan(src, tmp_path / "out.pdf", dpi=10)
    with pytest.raises(ValueError, match="unknown preset"):
        scan(src, tmp_path / "out.pdf", preset="ultra")
    with pytest.raises(TypeError):
        scan(src, tmp_path / "out.pdf", dpii=100)
    assert not (tmp_path / "out.pdf").exists()


def test_scan_refuses_to_overwrite_input(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf")
    with pytest.raises(ScannizerError, match="same"):
        scan(src, src)


def test_same_file_via_different_path(tmp_path, monkeypatch):
    src = make_text_pdf(tmp_path / "in.pdf")
    link = tmp_path / "link.pdf"
    link.symlink_to(src)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ScannizerError, match="same"):
        scan("in.pdf", link)
    assert src.stat().st_size > 0


def test_zero_pages(tmp_path):
    empty = tmp_path / "empty.pdf"
    doc = pdfium.PdfDocument.new()
    doc.save(empty)
    doc.close()
    # pdfium itself rejects a zero-page document, so the error comes from open_pdf;
    # the "no pages" guard in scan() stays as a backstop for lenient pdfium builds.
    with pytest.raises(ScannizerError):
        scan(empty, tmp_path / "out.pdf")
    assert not (tmp_path / "out.pdf").exists()


def test_encrypted_input(encrypted_pdf, tmp_path):
    with pytest.raises(ScannizerError, match="encrypted"):
        scan(encrypted_pdf, tmp_path / "out.pdf")


def test_missing_output_dir(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf")
    with pytest.raises(ScannizerError, match="directory"):
        scan(src, tmp_path / "nope" / "out.pdf", dpi=72)


def test_failure_leaves_no_partial_output(tmp_path, monkeypatch):
    src = make_text_pdf(tmp_path / "in.pdf", sizes=[(200, 200), (200, 200)])
    import scannizer.pipeline as pipeline

    calls = {"n": 0}
    real = pipeline.render_page

    def boom(doc, index, dpi):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("disk on fire")
        return real(doc, index, dpi)

    monkeypatch.setattr(pipeline, "render_page", boom)
    with pytest.raises(RuntimeError):
        scan(src, tmp_path / "out.pdf", dpi=72)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["in.pdf"]


def test_overwrites_existing_output(tmp_path):
    src = make_text_pdf(tmp_path / "in.pdf")
    dst = tmp_path / "out.pdf"
    dst.write_bytes(b"old")
    scan(src, dst, dpi=72)
    assert dst.stat().st_size > 100


def test_tiny_page(tmp_path):
    src = make_text_pdf(tmp_path / "tiny.pdf", sizes=[(40, 40)], text="x")
    scan(src, tmp_path / "out.pdf", preset="heavy", dpi=72)
    assert _page_sizes(tmp_path / "out.pdf") == [(40, 40)]


def test_rotated_page_keeps_orientation(tmp_path):
    src = make_text_pdf(tmp_path / "rot.pdf", sizes=[(595, 842)], rotation=90)
    scan(src, tmp_path / "out.pdf", dpi=72, seed=0)
    assert _page_sizes(tmp_path / "out.pdf") == [pytest.approx((842, 595))]
    assert render_pdf_page(tmp_path / "out.pdf").shape == (595, 842, 3)
