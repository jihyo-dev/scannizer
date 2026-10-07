# scannizer v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `scannizer input.pdf` 한 줄로 일반 PDF를 스캔본처럼 보이는 이미지 전용 PDF로 바꾸는 Python 라이브러리 + CLI를 만든다.

**Architecture:** pypdfium2로 페이지를 RGB 배열로 래스터화하고, `(image, rng, params) -> image` 순수 함수인 효과들을 물리적 순서(종이→접힘→기울기→광학→노이즈→색상)로 적용한 뒤, OpenCV로 JPEG 인코딩해 pypdfium2로 재인코딩 없이 PDF에 임베드한다. 페이지는 한 장씩 순차 처리하고 출력은 임시 파일에 쓴 뒤 `os.replace`로 교체한다.

**Tech Stack:** Python 3.10+, pypdfium2 5.x, numpy 2.x, opencv-python-headless 4.x/5.x, hatchling, pytest, ruff

**Spec:** `docs/superpowers/specs/2026-10-06-scannizer-design.md`

## Global Constraints

- Python 3.10 이상. 런타임 의존성은 `pypdfium2`, `numpy`, `opencv-python-headless` 세 개뿐 (PyMuPDF·Pillow 금지).
- 라이선스 MIT (`LICENSE` 파일, `pyproject.toml`의 `license`).
- 효과 함수는 RGB `uint8` `(H, W, 3)` 입력 → 같은 shape 반환 (색상 모드 단계만 `gray`/`bw`에서 `(H, W)`). 파일 I/O 금지, 난수는 전달받은 `numpy.random.Generator`만 사용.
- 강도 옵션이 0이면 효과는 입력을 그대로 반환한다.
- 픽셀 단위 값(블러 시그마, 음영 폭)은 200 DPI 기준으로 정의하고 실제 DPI에 비례해 조정한다.
- 옵션 범위: `dpi` 72–600, `color` ∈ {color, gray, bw}, `jpeg_quality` 1–95, `skew` 0–5, `fold` ∈ {none, half, trifold}, `fold_strength`/`noise`/`paper`/`edge_shadow`/`unevenness` 0–1, `blur` 0–3.
- CLI 종료 코드: 성공 0, `ScannizerError` 1 (트레이스백 없음), 인자 오류 2.
- 기본 출력 파일명: 입력과 같은 디렉터리의 `<이름>_scanned.pdf`.
- 출력 PDF: 원본과 페이지 수·크기(±1pt) 동일, 텍스트 레이어 없음, JPEG(`DCTDecode`) 임베드.
- 모든 커밋 메시지 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

스펙이 암시하지만 명시하지 않은 입력들. 각 항목의 테스트는 해당 태스크에 추가되어 있다.

1. **아주 작은 페이지(예: 40×40pt)** — 접힘 띠·가장자리 그림자 폭이 이미지보다 커도 크래시 없이 처리되어야 한다. → Task 10 `test_tiny_page`
2. **`/Rotate 90`이 걸린 페이지** — 렌더 결과와 출력 페이지 크기가 모두 회전 후 기준이어야 한다 (가로 페이지가 세로로 찌그러지면 안 됨). → Task 10 `test_rotated_page_keeps_orientation`
3. **출력 디렉터리가 존재하지 않음** — 트레이스백 대신 `ScannizerError`. → Task 10 `test_missing_output_dir`
4. **같은 파일을 다른 경로로 지정** (상대 경로 vs 절대 경로, 심볼릭 링크) — 입력 덮어쓰기 거부가 `resolve()` 기준이어야 한다. → Task 10 `test_same_file_via_different_path`
5. **`bw` 모드 + 거의 빈 페이지** — 이진화가 종이 결을 검은 점으로 만들거나 빈 페이지를 검게 만들면 안 된다. → Task 8 `test_bw_blank_page_stays_white`

---

## File Structure

| 파일 | 책임 |
|---|---|
| `pyproject.toml` | 패키지 메타데이터, 의존성, `scannizer` 스크립트, ruff/pytest 설정 |
| `LICENSE`, `README.md`, `.gitignore` | 배포 문서 |
| `src/scannizer/__init__.py` | `scan`, `ScanOptions`, `ScannizerError` 재수출 |
| `src/scannizer/errors.py` | `ScannizerError` |
| `src/scannizer/options.py` | `ScanOptions` dataclass + 범위 검증 + `replace()` |
| `src/scannizer/presets.py` | `PRESETS`, `get_preset()` |
| `src/scannizer/raster.py` | PDF 열기·검증(`open_pdf`), 페이지 렌더(`render_page`) |
| `src/scannizer/assemble.py` | `(jpeg, w, h)` 목록 → PDF 저장(`write_pdf`) |
| `src/scannizer/effects/common.py` | `scale_px`, `smooth_noise` 공용 헬퍼 |
| `src/scannizer/effects/paper.py` | `apply_paper` |
| `src/scannizer/effects/fold.py` | `fold_positions`, `apply_fold` |
| `src/scannizer/effects/geometry.py` | `sample_skew`, `apply_skew` |
| `src/scannizer/effects/optics.py` | `apply_edge_shadow`, `apply_unevenness`, `apply_blur` |
| `src/scannizer/effects/noise.py` | `apply_noise` |
| `src/scannizer/effects/color.py` | `apply_color_mode` |
| `src/scannizer/pipeline.py` | `scan()`, `process_page()`, `encode_jpeg()`, 원자적 저장 |
| `src/scannizer/cli.py` | argparse → `scan()` |
| `tests/conftest.py` | `make_text_pdf`, `render_pdf_page` 헬퍼, `fixtures/encrypted.pdf` |
| `tests/effects/test_*.py` | 효과별 단위 테스트 |
| `tests/test_options.py`, `test_raster.py`, `test_assemble.py`, `test_pipeline.py`, `test_cli.py` | 나머지 |
| `examples/make_samples.py` | 프리셋별 샘플 PDF 생성 |

환경: `.venv`는 이미 `uv venv`로 만들어져 있고 pypdfium2/numpy/opencv/pytest/ruff가 설치되어 있다. 모든 명령은 `/Users/joe/projects/chizi/scannizer`에서 `.venv/bin/python -m pytest ...` 형태로 실행한다. 작업 브랜치: `feat/v1` (main에서 분기).

---

### Task 1: 프로젝트 골격, 옵션, 프리셋, 오류

**Files:**
- Create: `pyproject.toml`, `LICENSE`, `.gitignore`, `README.md`
- Create: `src/scannizer/__init__.py`, `errors.py`, `options.py`, `presets.py`
- Test: `tests/test_options.py`

**Interfaces:**
- Produces: `ScannizerError(Exception)`; `ScanOptions` (frozen dataclass, 필드는 Global Constraints 표와 동일, `replace(**overrides) -> ScanOptions`); `COLOR_MODES`, `FOLD_PATTERNS` 튜플; `PRESETS: dict[str, ScanOptions]`; `get_preset(name: str) -> ScanOptions` (알 수 없는 이름이면 `ValueError`).

- [ ] **Step 1: 골격 파일 작성**

`pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "scannizer"
version = "0.1.0"
description = "Make a clean PDF look like it was scanned."
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
authors = [{ name = "Chizi" }]
keywords = ["pdf", "scan", "scanner", "noise", "augmentation"]
classifiers = [
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Topic :: Multimedia :: Graphics",
]
dependencies = [
  "pypdfium2>=4.30",
  "numpy>=1.26",
  "opencv-python-headless>=4.9",
]

[project.scripts]
scannizer = "scannizer.cli:main"

[project.urls]
Homepage = "https://github.com/chizi-develop/scannizer"

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:
```
.venv/
__pycache__/
*.pyc
dist/
build/
*.egg-info/
.pytest_cache/
.ruff_cache/
examples/output/
```

`LICENSE`: MIT 표준 문구, `Copyright (c) 2026 Chizi`.

`README.md` (초안, Task 13에서 완성):
```markdown
# scannizer

Make a clean PDF look like it was scanned.
```

- [ ] **Step 2: 실패하는 테스트 작성** — `tests/test_options.py`

```python
import pytest

from scannizer import ScanOptions, ScannizerError
from scannizer.options import COLOR_MODES, FOLD_PATTERNS
from scannizer.presets import PRESETS, get_preset


def test_defaults_equal_normal_preset():
    assert ScanOptions() == PRESETS["normal"]


@pytest.mark.parametrize(
    "field, value",
    [
        ("dpi", 71), ("dpi", 601),
        ("color", "rgb"),
        ("jpeg_quality", 0), ("jpeg_quality", 96),
        ("skew", -0.1), ("skew", 5.1),
        ("fold", "quarter"),
        ("fold_strength", 1.1), ("noise", -0.01), ("paper", 2),
        ("edge_shadow", 1.5), ("unevenness", -1), ("blur", 3.5),
    ],
)
def test_out_of_range_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        ScanOptions(**{field: value})


def test_boundaries_accepted():
    ScanOptions(dpi=72, jpeg_quality=1, skew=0, blur=0, noise=0)
    ScanOptions(dpi=600, jpeg_quality=95, skew=5, blur=3, noise=1)


def test_replace_overrides_and_validates():
    opts = get_preset("light").replace(fold="trifold", dpi=150)
    assert opts.fold == "trifold" and opts.dpi == 150
    assert opts.color == PRESETS["light"].color
    with pytest.raises(ValueError):
        get_preset("light").replace(dpi=10)
    with pytest.raises(TypeError):
        get_preset("light").replace(dpii=10)


def test_presets_and_enums():
    assert set(PRESETS) == {"light", "normal", "heavy"}
    assert PRESETS["heavy"].fold == "trifold" and PRESETS["heavy"].color == "gray"
    assert COLOR_MODES == ("color", "gray", "bw")
    assert FOLD_PATTERNS == ("none", "half", "trifold")
    with pytest.raises(ValueError, match="unknown preset"):
        get_preset("ultra")


def test_error_type():
    assert issubclass(ScannizerError, Exception)
```

- [ ] **Step 3: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_options.py -q`
Expected: ImportError (`scannizer` 없음)

- [ ] **Step 4: 구현**

`src/scannizer/errors.py`:
```python
class ScannizerError(Exception):
    """Raised for input/output problems scannizer can explain to the user."""
```

`src/scannizer/options.py`:
```python
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

COLOR_MODES = ("color", "gray", "bw")
FOLD_PATTERNS = ("none", "half", "trifold")

_RANGES: dict[str, tuple[float, float]] = {
    "dpi": (72, 600),
    "jpeg_quality": (1, 95),
    "skew": (0.0, 5.0),
    "fold_strength": (0.0, 1.0),
    "noise": (0.0, 1.0),
    "paper": (0.0, 1.0),
    "edge_shadow": (0.0, 1.0),
    "unevenness": (0.0, 1.0),
    "blur": (0.0, 3.0),
}


@dataclass(frozen=True)
class ScanOptions:
    """All knobs for one scan() run. Pixel-sized values are defined at 200 DPI."""

    dpi: int = 200
    color: str = "color"
    jpeg_quality: int = 75
    skew: float = 0.7
    fold: str = "none"
    fold_strength: float = 0.5
    noise: float = 0.3
    paper: float = 0.25
    edge_shadow: float = 0.25
    unevenness: float = 0.2
    blur: float = 0.6

    def __post_init__(self) -> None:
        for name, (lo, hi) in _RANGES.items():
            value = getattr(self, name)
            if not lo <= value <= hi:
                raise ValueError(f"{name} must be between {lo} and {hi}, got {value!r}")
        if self.color not in COLOR_MODES:
            raise ValueError(f"color must be one of {COLOR_MODES}, got {self.color!r}")
        if self.fold not in FOLD_PATTERNS:
            raise ValueError(f"fold must be one of {FOLD_PATTERNS}, got {self.fold!r}")

    def replace(self, **overrides) -> ScanOptions:
        """Return a copy with some fields changed. Unknown names raise TypeError."""
        return dataclasses.replace(self, **overrides)
```

`src/scannizer/presets.py`:
```python
from .options import ScanOptions

PRESETS: dict[str, ScanOptions] = {
    "light": ScanOptions(
        dpi=200, color="color", jpeg_quality=85, skew=0.3, fold="none", fold_strength=0.5,
        noise=0.15, paper=0.1, edge_shadow=0.1, unevenness=0.1, blur=0.3,
    ),
    "normal": ScanOptions(),
    "heavy": ScanOptions(
        dpi=150, color="gray", jpeg_quality=60, skew=1.5, fold="trifold", fold_strength=0.7,
        noise=0.55, paper=0.5, edge_shadow=0.5, unevenness=0.4, blur=1.0,
    ),
}


def get_preset(name: str) -> ScanOptions:
    try:
        return PRESETS[name]
    except KeyError:
        raise ValueError(f"unknown preset {name!r}; choose from {tuple(PRESETS)}") from None
```

`src/scannizer/__init__.py`:
```python
from .errors import ScannizerError
from .options import ScanOptions
from .pipeline import scan

__all__ = ["scan", "ScanOptions", "ScannizerError"]
```

`src/scannizer/pipeline.py` (임시 — Task 10에서 교체):
```python
def scan(src, dst, *, preset="normal", seed=None, **overrides) -> None:
    raise NotImplementedError
```

- [ ] **Step 5: 설치 후 통과 확인**

Run: `uv pip install -q --python .venv/bin/python -e . && .venv/bin/python -m pytest tests/test_options.py -q && .venv/bin/ruff check src tests`
Expected: 모두 PASS, ruff 경고 없음

- [ ] **Step 6: 커밋**

```bash
git add pyproject.toml LICENSE .gitignore README.md src tests
git commit -m "Add package skeleton, ScanOptions and presets"
```

---

### Task 2: 효과 공용 헬퍼

**Files:**
- Create: `src/scannizer/effects/__init__.py` (빈 파일), `src/scannizer/effects/common.py`
- Test: `tests/effects/__init__.py` (빈 파일), `tests/effects/test_common.py`

**Interfaces:**
- Produces: `scale_px(value: float, dpi: int) -> float` (200 DPI 기준 값을 실제 DPI로 환산); `smooth_noise(rng, shape: tuple[int, int], cells: int) -> np.ndarray` (float32, `[-1, 1]` 범위, `cells×cells` 격자 난수를 bicubic 보간한 저주파 노이즈); `to_float(img) -> np.ndarray` (float32 0–1); `to_uint8(img) -> np.ndarray` (clip 후 uint8).

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_common.py`

```python
import numpy as np

from scannizer.effects.common import scale_px, smooth_noise, to_float, to_uint8


def test_scale_px():
    assert scale_px(10, 200) == 10
    assert scale_px(10, 100) == 5
    assert scale_px(10, 400) == 20


def test_smooth_noise_shape_range_and_determinism():
    a = smooth_noise(np.random.default_rng(1), (64, 48), cells=4)
    b = smooth_noise(np.random.default_rng(1), (64, 48), cells=4)
    c = smooth_noise(np.random.default_rng(2), (64, 48), cells=4)
    assert a.shape == (64, 48) and a.dtype == np.float32
    assert a.min() >= -1 and a.max() <= 1
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_smooth_noise_is_smooth():
    n = smooth_noise(np.random.default_rng(0), (200, 200), cells=3)
    assert np.abs(np.diff(n, axis=0)).max() < 0.1


def test_smooth_noise_tiny_image():
    assert smooth_noise(np.random.default_rng(0), (2, 3), cells=8).shape == (2, 3)


def test_float_uint8_roundtrip():
    img = np.array([[[0, 128, 255]]], dtype=np.uint8)
    f = to_float(img)
    assert f.dtype == np.float32 and f[0, 0, 2] == 1.0
    assert np.array_equal(to_uint8(f), img)
    assert to_uint8(np.array([[-0.5, 1.5]], dtype=np.float32)).tolist() == [[0, 255]]
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_common.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/common.py`

```python
from __future__ import annotations

import cv2
import numpy as np

REFERENCE_DPI = 200


def scale_px(value: float, dpi: int) -> float:
    """Convert a pixel-sized value defined at 200 DPI to the given DPI."""
    return value * dpi / REFERENCE_DPI


def smooth_noise(rng: np.random.Generator, shape: tuple[int, int], cells: int) -> np.ndarray:
    """Low-frequency noise in [-1, 1]: a cells×cells random grid upscaled with bicubic."""
    h, w = shape
    grid = rng.uniform(-1.0, 1.0, size=(cells, cells)).astype(np.float32)
    up = cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
    return np.clip(up, -1.0, 1.0)


def to_float(img: np.ndarray) -> np.ndarray:
    return img.astype(np.float32) / 255.0


def to_uint8(img: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(img * 255.0), 0, 255).astype(np.uint8)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_common.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects tests/effects
git commit -m "Add shared effect helpers"
```

---

### Task 3: 종이 질감 효과

**Files:**
- Create: `src/scannizer/effects/paper.py`
- Test: `tests/effects/test_paper.py`

**Interfaces:**
- Consumes: `smooth_noise`, `to_float`, `to_uint8` from `effects.common`
- Produces: `apply_paper(img: np.ndarray, rng: np.random.Generator, strength: float, dpi: int) -> np.ndarray`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_paper.py`

```python
import numpy as np
import pytest

from scannizer.effects.paper import apply_paper


@pytest.fixture
def white():
    return np.full((120, 90, 3), 255, dtype=np.uint8)


def test_zero_strength_is_identity(white):
    out = apply_paper(white, np.random.default_rng(0), strength=0, dpi=200)
    assert np.array_equal(out, white)


def test_shape_dtype_and_determinism(white):
    a = apply_paper(white, np.random.default_rng(7), strength=0.5, dpi=200)
    b = apply_paper(white, np.random.default_rng(7), strength=0.5, dpi=200)
    c = apply_paper(white, np.random.default_rng(8), strength=0.5, dpi=200)
    assert a.shape == white.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_stronger_means_more_change(white):
    weak = apply_paper(white, np.random.default_rng(1), strength=0.2, dpi=200)
    strong = apply_paper(white, np.random.default_rng(1), strength=0.9, dpi=200)
    diff = lambda x: np.abs(x.astype(int) - 255).mean()  # noqa: E731
    assert 0 < diff(weak) < diff(strong)


def test_tint_is_warm(white):
    out = apply_paper(white, np.random.default_rng(1), strength=1.0, dpi=200).astype(int)
    assert out[..., 0].mean() > out[..., 2].mean()  # R stays above B
    assert out.mean() > 215  # still reads as white paper


def test_black_text_stays_dark():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    out = apply_paper(img, np.random.default_rng(1), strength=1.0, dpi=200)
    assert out.max() < 20
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_paper.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/paper.py`

```python
from __future__ import annotations

import numpy as np

from .common import smooth_noise, to_float, to_uint8

# Warm tint applied to white at full strength (multiplicative per RGB channel).
_TINT = np.array([1.0, 0.985, 0.955], dtype=np.float32)


def apply_paper(img: np.ndarray, rng: np.random.Generator, strength: float, dpi: int) -> np.ndarray:
    """Multiply the page by a paper-fibre texture and shift whites slightly warm."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    cells = max(2, int(round(max(h, w) / (40 * dpi / 200))))
    low = smooth_noise(rng, (h, w), cells=cells)            # broad mottling
    high = rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)  # fibre grain
    texture = 1.0 - strength * (0.03 * low + 0.012 * high)
    tint = 1.0 - strength * (1.0 - _TINT)
    out = to_float(img) * texture[..., None] * tint
    return to_uint8(out)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_paper.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects/paper.py tests/effects/test_paper.py
git commit -m "Add paper texture effect"
```

---

### Task 4: 접힘 효과

**Files:**
- Create: `src/scannizer/effects/fold.py`
- Test: `tests/effects/test_fold.py`

**Interfaces:**
- Consumes: `scale_px`, `to_float`, `to_uint8`
- Produces: `fold_positions(pattern: str) -> tuple[float, ...]` (페이지 높이 대비 비율, `none`→`()`, `half`→`(0.5,)`, `trifold`→`(1/3, 2/3)`); `apply_fold(img, rng, pattern: str, strength: float, dpi: int) -> np.ndarray`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_fold.py`

```python
import numpy as np
import pytest

from scannizer.effects.fold import apply_fold, fold_positions


@pytest.fixture
def white():
    return np.full((300, 200, 3), 255, dtype=np.uint8)


def test_fold_positions():
    assert fold_positions("none") == ()
    assert fold_positions("half") == (0.5,)
    assert fold_positions("trifold") == pytest.approx((1 / 3, 2 / 3))


def test_none_pattern_and_zero_strength_are_identity(white):
    assert np.array_equal(apply_fold(white, np.random.default_rng(0), "none", 0.8, 200), white)
    assert np.array_equal(apply_fold(white, np.random.default_rng(0), "half", 0.0, 200), white)


def test_shape_dtype_and_determinism(white):
    a = apply_fold(white, np.random.default_rng(3), "trifold", 0.6, 200)
    b = apply_fold(white, np.random.default_rng(3), "trifold", 0.6, 200)
    c = apply_fold(white, np.random.default_rng(4), "trifold", 0.6, 200)
    assert a.shape == white.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def _dark_rows(out):
    """Rows whose mean is clearly below the page's typical brightness."""
    row_mean = out.mean(axis=(1, 2))
    return np.flatnonzero(row_mean < np.median(row_mean) - 8)


def test_line_count_matches_pattern(white):
    for pattern, expected in [("half", 1), ("trifold", 2)]:
        out = apply_fold(white, np.random.default_rng(5), pattern, 0.8, 200)
        rows = _dark_rows(out)
        groups = 1 + int((np.diff(rows) > 3).sum()) if len(rows) else 0
        assert groups == expected, pattern


def test_lines_near_expected_positions(white):
    out = apply_fold(white, np.random.default_rng(5), "half", 1.0, 200)
    rows = _dark_rows(out)
    assert abs(rows.mean() - 150) < 300 * 0.02


def test_stronger_means_darker_line(white):
    weak = apply_fold(white, np.random.default_rng(1), "half", 0.2, 200)
    strong = apply_fold(white, np.random.default_rng(1), "half", 1.0, 200)
    assert weak.min() > strong.min()


def test_tiny_image_does_not_crash():
    tiny = np.full((5, 4, 3), 255, dtype=np.uint8)
    out = apply_fold(tiny, np.random.default_rng(0), "trifold", 1.0, 600)
    assert out.shape == tiny.shape
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_fold.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/fold.py`

```python
from __future__ import annotations

import math

import numpy as np

from .common import scale_px, to_float, to_uint8

_PATTERNS: dict[str, tuple[float, ...]] = {
    "none": (),
    "half": (0.5,),
    "trifold": (1 / 3, 2 / 3),
}


def fold_positions(pattern: str) -> tuple[float, ...]:
    """Fold line positions as fractions of page height."""
    return _PATTERNS[pattern]


def apply_fold(
    img: np.ndarray, rng: np.random.Generator, pattern: str, strength: float, dpi: int
) -> np.ndarray:
    """Draw horizontal fold creases: a dark band on one side, a light band on the other,
    plus a slightly different brightness for each folded panel."""
    positions = fold_positions(pattern)
    if not positions or strength <= 0:
        return img
    h, w = img.shape[:2]
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    shade = np.ones((h, w), dtype=np.float32)

    band = max(1.0, scale_px(6.0, dpi))
    for frac in positions:
        center = frac * h + rng.uniform(-0.01, 0.01) * h
        tilt = math.tan(math.radians(rng.uniform(-0.2, 0.2)))
        d = ys - (center + tilt * (xs - w / 2))  # signed distance from the crease
        dark = np.exp(-np.clip(-d, 0, None) / band) * (d <= 0)
        light = np.exp(-np.clip(d, 0, None) / (band * 1.5)) * (d > 0)
        shade *= 1.0 - strength * 0.35 * dark + strength * 0.06 * light

    # Each panel between creases gets its own slight brightness offset.
    edges = [0.0, *[p * h for p in positions], float(h)]
    for top, bottom in zip(edges[:-1], edges[1:]):
        offset = 1.0 + strength * rng.uniform(-0.03, 0.03)
        mask = (ys >= top) & (ys < bottom)
        shade *= np.where(mask, offset, 1.0).astype(np.float32)

    out = to_float(img) * shade[..., None]
    return to_uint8(out)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_fold.py -q && .venv/bin/ruff check src tests`
Expected: PASS. `test_line_count_matches_pattern`가 실패하면 `_dark_rows`의 임계값 8 또는 `0.35` 계수를 조정하되, 조정 후 이 계획에 반영한다.

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects/fold.py tests/effects/test_fold.py
git commit -m "Add fold crease effect"
```

---

### Task 5: 기울어짐 효과

**Files:**
- Create: `src/scannizer/effects/geometry.py`
- Test: `tests/effects/test_geometry.py`

**Interfaces:**
- Produces: `SCANNER_BED = (236, 236, 236)`; `sample_skew(rng, max_degrees: float, width: int, height: int) -> tuple[float, float, float]` → `(angle_deg, dx_px, dy_px)`; `apply_skew(img, rng, max_degrees: float) -> np.ndarray`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_geometry.py`

```python
import numpy as np

from scannizer.effects.geometry import SCANNER_BED, apply_skew, sample_skew


def test_sample_skew_within_bounds():
    rng = np.random.default_rng(0)
    for _ in range(200):
        angle, dx, dy = sample_skew(rng, 1.5, width=1000, height=1400)
        assert -1.5 <= angle <= 1.5
        assert abs(dx) <= 5 and abs(dy) <= 7  # 0.5 % of each dimension


def test_zero_max_is_identity():
    img = np.random.default_rng(0).integers(0, 255, (80, 60, 3), dtype=np.uint8)
    assert np.array_equal(apply_skew(img, np.random.default_rng(0), 0.0), img)


def test_shape_dtype_determinism():
    img = np.full((200, 150, 3), 255, dtype=np.uint8)
    a = apply_skew(img, np.random.default_rng(1), 2.0)
    b = apply_skew(img, np.random.default_rng(1), 2.0)
    c = apply_skew(img, np.random.default_rng(2), 2.0)
    assert a.shape == img.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_exposed_corners_are_scanner_bed():
    img = np.zeros((300, 300, 3), dtype=np.uint8)  # black page makes corners obvious
    out = apply_skew(img, np.random.default_rng(3), 5.0)
    corners = [out[0, 0], out[0, -1], out[-1, 0], out[-1, -1]]
    assert any(tuple(c) == SCANNER_BED for c in corners)


def test_rotation_actually_rotates():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    img[100, :] = 255  # horizontal white line
    out = apply_skew(img, np.random.default_rng(4), 5.0)
    ys = np.flatnonzero(out[:, :, 0].max(axis=1) > 128)
    assert ys.max() - ys.min() > 3  # line now spans several rows
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_geometry.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/geometry.py`

```python
from __future__ import annotations

import cv2
import numpy as np

SCANNER_BED = (236, 236, 236)  # light grey seen where the page does not cover the glass


def sample_skew(
    rng: np.random.Generator, max_degrees: float, width: int, height: int
) -> tuple[float, float, float]:
    """Random rotation angle (deg) and translation (px) for one page."""
    angle = float(rng.uniform(-max_degrees, max_degrees))
    dx = float(rng.uniform(-0.005, 0.005) * width)
    dy = float(rng.uniform(-0.005, 0.005) * height)
    return angle, dx, dy


def apply_skew(img: np.ndarray, rng: np.random.Generator, max_degrees: float) -> np.ndarray:
    """Rotate and shift the page slightly, keeping the canvas size."""
    if max_degrees <= 0:
        return img
    h, w = img.shape[:2]
    angle, dx, dy = sample_skew(rng, max_degrees, w, h)
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    matrix[:, 2] += (dx, dy)
    return cv2.warpAffine(
        img, matrix, (w, h),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=SCANNER_BED,
    )
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_geometry.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects/geometry.py tests/effects/test_geometry.py
git commit -m "Add skew effect"
```

---

### Task 6: 광학 효과 (가장자리 그림자, 밝기 불균일, 블러)

**Files:**
- Create: `src/scannizer/effects/optics.py`
- Test: `tests/effects/test_optics.py`

**Interfaces:**
- Consumes: `smooth_noise`, `scale_px`, `to_float`, `to_uint8`
- Produces: `apply_edge_shadow(img, rng, strength, dpi)`, `apply_unevenness(img, rng, strength)`, `apply_blur(img, sigma, dpi)` — 모두 `np.ndarray` 반환

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_optics.py`

```python
import numpy as np
import pytest

from scannizer.effects.optics import apply_blur, apply_edge_shadow, apply_unevenness


@pytest.fixture
def white():
    return np.full((200, 160, 3), 255, dtype=np.uint8)


def test_identities(white):
    rng = np.random.default_rng(0)
    assert np.array_equal(apply_edge_shadow(white, rng, 0, 200), white)
    assert np.array_equal(apply_unevenness(white, rng, 0), white)
    assert np.array_equal(apply_blur(white, 0, 200), white)


def test_edge_shadow_darkens_edges_not_center(white):
    out = apply_edge_shadow(white, np.random.default_rng(1), 1.0, 200).astype(int)
    assert out[100, 80].min() > 245
    assert out[0, 80].max() < 245 or out[-1, 80].max() < 245
    assert out[100, 0].max() < 245 or out[100, -1].max() < 245


def test_edge_shadow_determinism_and_strength(white):
    a = apply_edge_shadow(white, np.random.default_rng(2), 0.5, 200)
    b = apply_edge_shadow(white, np.random.default_rng(2), 0.5, 200)
    strong = apply_edge_shadow(white, np.random.default_rng(2), 1.0, 200)
    assert np.array_equal(a, b)
    assert a.min() > strong.min()


def test_unevenness_is_smooth_gradient(white):
    out = apply_unevenness(white, np.random.default_rng(3), 1.0).astype(int)
    assert out.min() < 250  # some darkening happened
    assert np.abs(np.diff(out[..., 0], axis=1)).max() <= 2  # no hard steps
    assert np.array_equal(out, apply_unevenness(white, np.random.default_rng(3), 1.0))


def test_blur_spreads_a_line():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    img[25, :] = 255
    out = apply_blur(img, 1.0, 200)
    assert out.shape == img.shape and out.dtype == np.uint8
    assert out[24, 25, 0] > 0 and out[26, 25, 0] > 0
    assert out[25, 25, 0] < 255


def test_blur_scales_with_dpi():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    img[25, :] = 255
    low = apply_blur(img, 1.0, 100)
    high = apply_blur(img, 1.0, 400)
    assert high[22, 25, 0] > low[22, 25, 0]


def test_tiny_image_edge_shadow():
    tiny = np.full((3, 3, 3), 255, dtype=np.uint8)
    assert apply_edge_shadow(tiny, np.random.default_rng(0), 1.0, 600).shape == tiny.shape
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_optics.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/optics.py`

```python
from __future__ import annotations

import math

import cv2
import numpy as np

from .common import scale_px, smooth_noise, to_float, to_uint8


def apply_edge_shadow(
    img: np.ndarray, rng: np.random.Generator, strength: float, dpi: int
) -> np.ndarray:
    """Darken the four page edges with an exponential falloff; each edge differs a little."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    ys = np.arange(h, dtype=np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    width = max(1.0, scale_px(60.0, dpi))
    depth = 0.35 * strength
    shade = np.ones((h, w), dtype=np.float32)
    for dist in (ys, h - 1 - ys, xs, w - 1 - xs):
        edge_strength = depth * rng.uniform(0.3, 1.0)
        shade *= 1.0 - edge_strength * np.exp(-dist / width)
    return to_uint8(to_float(img) * shade[..., None])


def apply_unevenness(img: np.ndarray, rng: np.random.Generator, strength: float) -> np.ndarray:
    """Multiply by a gentle brightness map: a linear gradient in a random direction
    plus low-frequency mottling (lamp falloff, slightly lifted paper)."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    theta = rng.uniform(0, 2 * math.pi)
    ys = (np.arange(h, dtype=np.float32) / max(h - 1, 1) - 0.5)[:, None]
    xs = (np.arange(w, dtype=np.float32) / max(w - 1, 1) - 0.5)[None, :]
    gradient = xs * math.cos(theta) + ys * math.sin(theta)  # [-0.7, 0.7]
    mottle = smooth_noise(rng, (h, w), cells=4)
    shade = 1.0 - strength * 0.12 * (1.0 + 0.8 * gradient + 0.5 * mottle) / 2.3
    return to_uint8(to_float(img) * shade[..., None])


def apply_blur(img: np.ndarray, sigma: float, dpi: int) -> np.ndarray:
    """Gaussian blur; sigma is given in pixels at 200 DPI."""
    if sigma <= 0:
        return img
    s = scale_px(sigma, dpi)
    return cv2.GaussianBlur(img, (0, 0), sigmaX=s, sigmaY=s)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_optics.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects/optics.py tests/effects/test_optics.py
git commit -m "Add edge shadow, unevenness and blur effects"
```

---

### Task 7: 노이즈 효과

**Files:**
- Create: `src/scannizer/effects/noise.py`
- Test: `tests/effects/test_noise.py`

**Interfaces:**
- Produces: `apply_noise(img, rng, strength: float) -> np.ndarray`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_noise.py`

```python
import numpy as np

from scannizer.effects.noise import apply_noise


def test_zero_is_identity():
    img = np.full((40, 40, 3), 200, dtype=np.uint8)
    assert np.array_equal(apply_noise(img, np.random.default_rng(0), 0), img)


def test_shape_dtype_determinism():
    img = np.full((40, 40, 3), 200, dtype=np.uint8)
    a = apply_noise(img, np.random.default_rng(1), 0.5)
    b = apply_noise(img, np.random.default_rng(1), 0.5)
    c = apply_noise(img, np.random.default_rng(2), 0.5)
    assert a.shape == img.shape and a.dtype == np.uint8
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_strength_controls_spread():
    img = np.full((200, 200, 3), 128, dtype=np.uint8)
    weak = apply_noise(img, np.random.default_rng(1), 0.2).astype(float)
    strong = apply_noise(img, np.random.default_rng(1), 1.0).astype(float)
    assert 0 < weak.std() < strong.std()
    assert abs(strong.mean() - 128) < 1.5  # zero-mean noise
    assert strong.std() < 20  # still readable


def test_mostly_luminance_noise():
    img = np.full((200, 200, 3), 128, dtype=np.uint8)
    out = apply_noise(img, np.random.default_rng(1), 1.0).astype(float)
    channel_spread = (out.max(axis=2) - out.min(axis=2)).mean()
    luma_spread = out.mean(axis=2).std()
    assert channel_spread < luma_spread
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_noise.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/noise.py`

```python
from __future__ import annotations

import numpy as np


def apply_noise(img: np.ndarray, rng: np.random.Generator, strength: float) -> np.ndarray:
    """Sensor grain: shared luminance noise plus a weaker per-channel component."""
    if strength <= 0:
        return img
    h, w = img.shape[:2]
    luma = rng.normal(0.0, 12.0 * strength, size=(h, w, 1)).astype(np.float32)
    chroma = rng.normal(0.0, 3.0 * strength, size=(h, w, img.shape[2])).astype(np.float32)
    out = img.astype(np.float32) + luma + chroma
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_noise.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects/noise.py tests/effects/test_noise.py
git commit -m "Add sensor noise effect"
```

---

### Task 8: 색상 모드 효과

**Files:**
- Create: `src/scannizer/effects/color.py`
- Test: `tests/effects/test_color.py`

**Interfaces:**
- Produces: `apply_color_mode(img, mode: str) -> np.ndarray` — `color`: 입력 그대로 `(H,W,3)`; `gray`: `(H,W)` uint8; `bw`: `(H,W)` uint8, 값은 0/255만

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/effects/test_color.py`

```python
import numpy as np

from scannizer.effects.color import apply_color_mode


def _page():
    img = np.full((60, 80, 3), 240, dtype=np.uint8)
    img[20:40, 10:70] = (30, 30, 30)  # dark text block
    img[5:10, 5:10] = (200, 30, 30)  # red stamp
    return img


def test_color_is_identity():
    img = _page()
    assert apply_color_mode(img, "color") is img


def test_gray_is_single_channel_luminance():
    out = apply_color_mode(_page(), "gray")
    assert out.shape == (60, 80) and out.dtype == np.uint8
    assert out[0, 0] == 240 and out[30, 40] == 30
    assert 60 < out[7, 7] < 120  # red stamp becomes mid-dark grey


def test_bw_is_binary():
    out = apply_color_mode(_page(), "bw")
    assert out.shape == (60, 80) and out.dtype == np.uint8
    assert set(np.unique(out).tolist()) <= {0, 255}
    assert out[0, 0] == 255 and out[30, 40] == 0


def test_bw_blank_page_stays_white():
    blank = np.full((60, 80, 3), 235, dtype=np.uint8)
    blank[::7, ::5] = 225  # faint paper grain
    out = apply_color_mode(blank, "bw")
    assert (out == 255).mean() > 0.99
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_color.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/effects/color.py`

```python
from __future__ import annotations

import cv2
import numpy as np

# Fixed threshold: Otsu would split a blank page's grain into black and white.
_BW_THRESHOLD = 140


def apply_color_mode(img: np.ndarray, mode: str) -> np.ndarray:
    """Keep colour, convert to 8-bit grey, or binarise."""
    if mode == "color":
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    if mode == "gray":
        return gray
    _, bw = cv2.threshold(gray, _BW_THRESHOLD, 255, cv2.THRESH_BINARY)
    return bw
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/effects/test_color.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/effects/color.py tests/effects/test_color.py
git commit -m "Add colour mode effect"
```

---

### Task 9: PDF 래스터화와 조립

**Files:**
- Create: `src/scannizer/raster.py`, `src/scannizer/assemble.py`
- Create: `tests/conftest.py`, `tests/fixtures/encrypted.pdf`
- Test: `tests/test_raster.py`, `tests/test_assemble.py`

**Interfaces:**
- Consumes: `ScannizerError`
- Produces:
  - `raster.open_pdf(path: Path) -> pdfium.PdfDocument` — 없음/PDF 아님/암호화 → `ScannizerError`
  - `raster.render_page(doc, index: int, dpi: int) -> np.ndarray` RGB uint8 `(H, W, 3)`; 페이지 `/Rotate` 반영
  - `assemble.write_pdf(pages: Iterable[tuple[bytes, float, float]], dst: Path) -> None` — `(jpeg_bytes, width_pt, height_pt)`
  - `tests/conftest.py`: `make_text_pdf(path, sizes=[(595, 842)], text="Hello scannizer", rotation=0) -> Path`, `render_pdf_page(path, index=0, scale=1.0) -> np.ndarray(RGB)`, `encrypted_pdf` fixture

- [ ] **Step 1: 암호화 픽스처 생성**

```bash
mkdir -p tests/fixtures
.venv/bin/python -c "
import pypdfium2 as pdfium
d = pdfium.PdfDocument.new(); d.new_page(200, 100); d.save('tests/fixtures/plain.pdf')"
qpdf --encrypt user owner 256 -- tests/fixtures/plain.pdf tests/fixtures/encrypted.pdf
rm tests/fixtures/plain.pdf
```

- [ ] **Step 2: conftest 작성** — `tests/conftest.py`

```python
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
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_raster.py`:
```python
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
```

`tests/test_assemble.py`:
```python
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
```

- [ ] **Step 4: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_raster.py tests/test_assemble.py -q`
Expected: ModuleNotFoundError (`scannizer.raster`)

- [ ] **Step 5: 구현**

`src/scannizer/raster.py`:
```python
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
```

`src/scannizer/assemble.py`:
```python
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
```

- [ ] **Step 6: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_raster.py tests/test_assemble.py -q && .venv/bin/ruff check src tests`
Expected: PASS. `render` 호출에서 `rev_byteorder` 인자가 거부되면 `bitmap.mode`를 확인해 `BGR`이면 `[..., ::-1]`로 뒤집는 분기로 대체한다.

- [ ] **Step 7: 커밋**

```bash
git add src/scannizer/raster.py src/scannizer/assemble.py tests/conftest.py tests/fixtures tests/test_raster.py tests/test_assemble.py
git commit -m "Add PDF rasterisation and JPEG page assembly"
```

---

### Task 10: 파이프라인 (`scan`)

**Files:**
- Modify: `src/scannizer/pipeline.py` (Task 1의 임시 구현 교체)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: 모든 효과 함수, `open_pdf`, `render_page`, `write_pdf`, `get_preset`, `ScanOptions.replace`
- Produces: `scan(src, dst, *, preset="normal", seed=None, **overrides) -> None`; `process_page(img, rng, opts: ScanOptions) -> np.ndarray`; `encode_jpeg(img, quality: int) -> bytes`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_pipeline.py`

```python
import numpy as np
import pypdfium2 as pdfium
import pytest

from scannizer import ScanOptions, ScannizerError, scan
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
    assert not np.array_equal(render_pdf_page(tmp_path / "out.pdf", 0),
                              render_pdf_page(tmp_path / "out.pdf", 1))


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
    with pytest.raises(ScannizerError, match="no pages"):
        scan(empty, tmp_path / "out.pdf")


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
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_pipeline.py -q`
Expected: ImportError (`encode_jpeg`, `process_page` 없음)

- [ ] **Step 3: 구현** — `src/scannizer/pipeline.py`

```python
from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

from .assemble import write_pdf
from .effects.color import apply_color_mode
from .effects.fold import apply_fold
from .effects.geometry import apply_skew
from .effects.noise import apply_noise
from .effects.optics import apply_blur, apply_edge_shadow, apply_unevenness
from .effects.paper import apply_paper
from .errors import ScannizerError
from .options import ScanOptions
from .presets import get_preset
from .raster import open_pdf, render_page


def scan(
    src: str | os.PathLike,
    dst: str | os.PathLike,
    *,
    preset: str = "normal",
    seed: int | None = None,
    **overrides,
) -> None:
    """Render every page of `src`, apply scanner effects and write an image-only PDF to `dst`.

    `overrides` are ScanOptions field names and take precedence over the preset.
    """
    opts = get_preset(preset).replace(**overrides)
    src_path, dst_path = Path(src), Path(dst)
    if src_path.exists() and src_path.resolve() == dst_path.resolve():
        raise ScannizerError("output path is the same file as the input")
    if not dst_path.parent.is_dir():
        raise ScannizerError(f"output directory does not exist: {dst_path.parent}")

    doc = open_pdf(src_path)
    try:
        count = len(doc)
        if count == 0:
            raise ScannizerError(f"PDF has no pages: {src_path}")
        rngs = [np.random.default_rng(s) for s in np.random.SeedSequence(seed).spawn(count)]

        def pages() -> Iterator[tuple[bytes, float, float]]:
            for index in range(count):
                width, height = doc.get_page_size(index)
                img = render_page(doc, index, opts.dpi)
                out = process_page(img, rngs[index], opts)
                yield encode_jpeg(out, opts.jpeg_quality), width, height

        _write_atomically(pages(), dst_path)
    finally:
        doc.close()


def process_page(img: np.ndarray, rng: np.random.Generator, opts: ScanOptions) -> np.ndarray:
    """Apply the effects in physical order: paper → fold → skew → optics → noise → colour."""
    img = apply_paper(img, rng, opts.paper, opts.dpi)
    img = apply_fold(img, rng, opts.fold, opts.fold_strength, opts.dpi)
    img = apply_skew(img, rng, opts.skew)
    img = apply_edge_shadow(img, rng, opts.edge_shadow, opts.dpi)
    img = apply_unevenness(img, rng, opts.unevenness)
    img = apply_blur(img, opts.blur, opts.dpi)
    img = apply_noise(img, rng, opts.noise)
    return apply_color_mode(img, opts.color)


def encode_jpeg(img: np.ndarray, quality: int) -> bytes:
    """JPEG-encode an RGB (H, W, 3) or grey (H, W) uint8 array."""
    if img.ndim == 3:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise ScannizerError("JPEG encoding failed")
    return buf.tobytes()


def _write_atomically(pages: Iterator[tuple[bytes, float, float]], dst: Path) -> None:
    """Write to a temp file next to `dst`, then rename, so a crash never leaves a half PDF."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{dst.name}.", suffix=".tmp", dir=dst.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        write_pdf(pages, tmp)
        os.replace(tmp, dst)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_pipeline.py -q && .venv/bin/ruff check src tests`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/pipeline.py tests/test_pipeline.py
git commit -m "Add scan() pipeline with atomic output"
```

---

### Task 11: CLI

**Files:**
- Create: `src/scannizer/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `scan`, `ScannizerError`, `PRESETS`, `COLOR_MODES`, `FOLD_PATTERNS`
- Produces: `main(argv: list[str] | None = None) -> int`; `default_output(src: Path) -> Path`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_cli.py`

```python
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
    args = [str(src), "-o", str(out), "--preset", "heavy", "--seed", "1", "--dpi", "72",
            "--color", "bw", "--fold", "half", "--noise", "0", "--blur", "0"]
    assert main(args) == 0
    page = render_pdf_page(out)
    assert page.shape[2] == 3  # pdfium renders grey JPEG to RGB


def test_seed_reproducible_via_cli(tmp_path):
    src = make_text_pdf(tmp_path / "doc.pdf")
    main([str(src), "-o", str(tmp_path / "a.pdf"), "--seed", "9", "--dpi", "72"])
    main([str(src), "-o", str(tmp_path / "b.pdf"), "--seed", "9", "--dpi", "72"])
    assert (tmp_path / "a.pdf").read_bytes() == (tmp_path / "b.pdf").read_bytes()


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
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/test_cli.py -q`
Expected: ModuleNotFoundError

- [ ] **Step 3: 구현** — `src/scannizer/cli.py`

```python
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
```

- [ ] **Step 4: 통과 확인**

Run: `.venv/bin/python -m pytest tests/test_cli.py -q && .venv/bin/ruff check src tests && .venv/bin/scannizer --help | head -3`
Expected: PASS, 도움말 출력

- [ ] **Step 5: 커밋**

```bash
git add src/scannizer/cli.py tests/test_cli.py
git commit -m "Add scannizer command-line interface"
```

---

### Task 12: 샘플 생성 스크립트와 시각 검수·프리셋 조정

**Files:**
- Create: `examples/make_samples.py`
- Modify (조정 시): `src/scannizer/presets.py`, 효과 계수, 스펙 5장 프리셋 표

- [ ] **Step 1: 스크립트 작성** — `examples/make_samples.py`

```python
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
```

- [ ] **Step 2: 샘플 생성 후 PNG로 렌더해 눈으로 확인**

```bash
.venv/bin/python examples/make_samples.py
.venv/bin/python -c "
import pypdfium2 as pdfium, pathlib
for p in sorted(pathlib.Path('examples/output').glob('sample_*.pdf')):
    pdfium.PdfDocument(p)[0].render(scale=1).to_pil().save(p.with_suffix('.png'))
"
```
각 PNG를 Read 도구로 열어 확인한다. 기준: 텍스트가 읽힘, 흰 종이가 흰색으로 보임(회색 아님), 접힘선이 띠가 아니라 선으로 보임, 가장자리 그림자가 과하지 않음, 붉은 도장이 `color`에서 유지됨.

- [ ] **Step 3: 조정**

과하거나 약한 효과가 있으면 효과 모듈의 계수(`0.35`, `0.12`, `12.0` 등)나 `presets.py` 값을 바꾸고 전체 테스트를 다시 돌린다. 바뀐 프리셋 값은 스펙 5장 표에도 반영한다.

- [ ] **Step 4: 전체 테스트와 린트**

Run: `.venv/bin/python -m pytest -q && .venv/bin/ruff check src tests examples && .venv/bin/ruff format --check src tests examples`
Expected: 모두 통과 (format 불일치는 `ruff format` 실행)

- [ ] **Step 5: 커밋**

```bash
git add examples/make_samples.py src docs
git commit -m "Add sample generator and tune presets from visual review"
```

---

### Task 13: README와 배포 준비

**Files:**
- Modify: `README.md`

- [ ] **Step 1: README 작성**

```markdown
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
```

- [ ] **Step 2: 패키지 빌드 확인**

Run: `uv build 2>&1 | tail -2 && ls dist/`
Expected: `scannizer-0.1.0-py3-none-any.whl`, `scannizer-0.1.0.tar.gz`

- [ ] **Step 3: 깨끗한 환경에서 설치·실행 확인**

```bash
rm -rf /tmp/scannizer-check && uv venv -q /tmp/scannizer-check && uv pip install -q --python /tmp/scannizer-check/bin/python dist/*.whl && /tmp/scannizer-check/bin/scannizer examples/output/source.pdf -o /tmp/scannizer-check/out.pdf && ls -la /tmp/scannizer-check/out.pdf && rm -rf /tmp/scannizer-check dist
```
Expected: out.pdf 생성

- [ ] **Step 4: 커밋**

```bash
git add README.md
git commit -m "Write README"
```

---

## Self-Review

- **Spec coverage**: §2 흐름·원자적 저장 → Task 10; §3 효과 9종 → Task 3–8; §4 난수 → Task 10 (`SeedSequence.spawn`); §5 API·옵션·프리셋 → Task 1, 10; §6 CLI → Task 11; §7 오류 표 → Task 9(열기), 10(0페이지·같은 경로), 11(종료 코드); §8 모듈 → File Structure; §9 의존성 → Task 1 pyproject; §10 테스트 → 각 태스크; §11 PyPI 이름 → 확인 완료(사용 가능).
- **Placeholder scan**: 없음.
- **Type consistency**: `apply_blur(img, sigma, dpi)`는 rng를 받지 않음 — Task 6과 Task 10 호출이 일치. `apply_color_mode(img, mode)` 동일. `render_page(doc, index, dpi)` Task 9·10 일치. `write_pdf(pages, dst)` Task 9·10 일치.
- **Review Focus**: 5항목 모두 Task 8/10에 테스트 존재.
