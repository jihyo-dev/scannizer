from pathlib import Path

import pytest

from scannizer.cli import default_output, main
from tests.conftest import make_text_pdf, render_pdf_page


def test_default_output_name():
    assert default_output(Path("/a/b/report.pdf")) == Path("/a/b/report_scanned.pdf")
    assert default_output(Path("x.PDF")) == Path("x_scanned.pdf")


def test_basic_run_creates_default_output(tmp_path):
    src = make_text_pdf(tmp_path / "doc.pdf")
    assert main([str(src), "--dpi", "72"]) == 0
    assert (tmp_path / "doc_scanned.pdf").exists()


def test_explicit_output_and_options(tmp_path):
    src = make_text_pdf(tmp_path / "doc.pdf")
    out = tmp_path / "o.pdf"
    args = [
        str(src), "-o", str(out), "--preset", "heavy", "--seed", "1", "--dpi", "72",
        "--color", "bw", "--fold", "half", "--noise", "0", "--blur", "0",
    ]  # fmt: skip
    assert main(args) == 0
    page = render_pdf_page(out)
    assert page.shape[2] == 3  # pdfium renders grey JPEG to RGB


def test_seed_reproducible_via_cli(tmp_path):
    src = make_text_pdf(tmp_path / "doc.pdf")
    main([str(src), "-o", str(tmp_path / "a.pdf"), "--seed", "9", "--dpi", "72"])
    main([str(src), "-o", str(tmp_path / "b.pdf"), "--seed", "9", "--dpi", "72"])
    # pdfium writes a random /ID into every file, so compare rendered pixels, not bytes.
    import numpy as np

    assert np.array_equal(render_pdf_page(tmp_path / "a.pdf"), render_pdf_page(tmp_path / "b.pdf"))


def test_scannizer_error_exits_1_without_traceback(tmp_path, capsys):
    assert main([str(tmp_path / "missing.pdf")]) == 1
    err = capsys.readouterr().err
    assert "not found" in err and "Traceback" not in err


def test_bad_option_exits_2(tmp_path, capsys):
    src = make_text_pdf(tmp_path / "doc.pdf")
    with pytest.raises(SystemExit) as exc:
        main([str(src), "--dpi", "10"])
    assert exc.value.code == 2
    assert "dpi" in capsys.readouterr().err
    with pytest.raises(SystemExit) as exc:
        main([str(src), "--preset", "ultra"])
    assert exc.value.code == 2


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "scannizer" in capsys.readouterr().out
