# scannizer v1 설계

- 작성일: 2026-10-06
- 상태: 검토 대기

## 1. 목적

일반 PDF를 실제 스캐너로 스캔한 문서처럼 보이게 변환하는 Python 라이브러리 겸 CLI.

- **주 용도**: 직접 만든 PDF(계약서, 신청서 등)를 스캔본 형태로 제출·공유
- **배포**: MIT 라이선스 오픈소스, PyPI 패키지 `scannizer`
- **사용자**: `pip install` 후 명령 한 줄로 쓰는 일반 사용자, 자기 코드에서 `scan()`을 호출하는 개발자

### 성공 기준

1. `scannizer input.pdf` 한 줄로 `input_scanned.pdf`가 생성된다.
2. 기본 프리셋 출력이 사무실 복합기 스캔본처럼 보이고, 효과가 과해서 인위적으로 보이지 않는다. (자동 검증 불가, `examples/` 샘플로 직접 확인)
3. 같은 시드를 주면 같은 결과가 나온다.
4. 출력 PDF는 원본과 페이지 수·페이지 크기가 같고 텍스트 레이어가 없다.

### v1 제외 범위

오염·흔적(먼지, 얼룩, 스테이플·펀치 자국), 종이가 휘는 3D 변형, OCR 텍스트 레이어 추가, 이미지(JPG/PNG) 입력, 암호화 PDF, 병렬 처리, GUI·웹.

## 2. 처리 흐름

```
입력 PDF
  → 래스터화 (pypdfium2, 페이지 → RGB uint8 배열)
  → 효과 파이프라인 (NumPy / OpenCV)
  → JPEG 인코딩 (OpenCV)
  → PDF 조립 (pypdfium2, JPEG 바이트를 재인코딩 없이 임베드)
  → 출력 PDF
```

- 한 페이지씩 순차 처리한다. 메모리에는 현재 페이지의 배열과 지금까지 인코딩된 JPEG 바이트만 남는다.
- 출력 페이지 크기(pt)는 원본 페이지 크기와 같다.
- 출력은 같은 디렉터리의 임시 파일에 쓴 뒤 `os.replace`로 교체한다. 중간에 실패해도 불완전한 출력 파일이 남지 않는다.

## 3. 효과

실제 종이가 스캐너를 거치는 물리적 순서대로 적용한다. 픽셀 단위 크기를 갖는 값(블러 시그마, 음영 폭 등)은 200 DPI 기준으로 정의하고 실제 DPI에 비례해 조정한다.

| 순서 | 효과 | 옵션 | 동작 |
|---|---|---|---|
| 1 | 종이 질감 | `paper` | 저주파·고주파 노이즈를 합친 종이 결 텍스처를 곱하고, 흰색을 따뜻한 색조로 약하게 이동 |
| 2 | 접힘 | `fold`, `fold_strength` | 접힘선마다 한쪽은 어둡고 한쪽은 밝은 좁은 음영 띠를 넣고, 접힌 면마다 밝기를 미세하게 다르게 함 |
| 3 | 기울어짐 | `skew` | `[-skew, +skew]`도 범위의 랜덤 회전 + 페이지 폭의 ±0.5% 이내 이동. 캔버스 크기 유지, 빈 영역은 스캐너 바닥색(밝은 회색)으로 채움 |
| 4 | 가장자리 그림자 | `edge_shadow` | 네 변에서 안쪽으로 감쇠하는 어두운 그라디언트. 변마다 세기가 랜덤하게 다름 |
| 5 | 밝기 불균일 | `unevenness` | 랜덤 방향의 선형 그라디언트와 저주파 노이즈를 합친 밝기 맵을 곱함 |
| 6 | 블러 | `blur` | 가우시안 블러, 값은 시그마(px) |
| 7 | 노이즈 | `noise` | 휘도 공통 가우시안 그레인 + 약한 채널별 노이즈 |
| 8 | 색상 모드 | `color` | `color`: 유지 / `gray`: 휘도 변환 / `bw`: 휘도 변환 후 이진화 |
| 9 | JPEG 압축 | `jpeg_quality` | 지정 품질로 인코딩 (`bw`도 8비트 그레이 JPEG) |

### 접힘 패턴

- `none`: 적용 안 함
- `half`: 페이지 높이 1/2 지점의 가로 접힘선 1개
- `trifold`: 높이 1/3, 2/3 지점의 가로 접힘선 2개 (편지 3단 접기)

접힘선 위치는 페이지 높이의 ±1% 이내, 기울기는 ±0.2° 이내에서 랜덤하게 흔든다.

### 공통 규칙

- 효과 함수는 RGB `uint8` 배열 `(H, W, 3)`을 받아 같은 형태로 반환한다. 색상 모드 단계만 `gray`/`bw`일 때 `(H, W)`를 반환한다.
- 강도 옵션이 0이면 해당 효과는 입력을 그대로 반환한다.
- 효과 함수는 파일 I/O를 하지 않고, 난수는 전달받은 `numpy.random.Generator`만 쓴다.

## 4. 난수와 재현성

- `numpy.random.SeedSequence(seed).spawn(페이지 수)`로 페이지별 독립 생성기를 만든다.
- `seed=None`이면 OS 엔트로피를 쓴다(매번 다른 결과).
- 같은 입력·옵션·시드는 같은 페이지 픽셀을 만든다.

## 5. 공개 API

```python
from scannizer import scan, ScanOptions, ScannizerError

scan("in.pdf", "out.pdf")
scan("in.pdf", "out.pdf", preset="heavy", seed=42)
scan("in.pdf", "out.pdf", fold="trifold", color="gray")
```

```python
def scan(src, dst, *, preset="normal", seed=None, **overrides) -> None
```

- `src`, `dst`: `str` 또는 `os.PathLike`
- `overrides`: `ScanOptions` 필드명. 프리셋 값 위에 덮어쓴다.

### ScanOptions

불변 dataclass. 생성 시 범위를 검증한다.

| 필드 | 타입 | 범위 |
|---|---|---|
| `dpi` | int | 72–600 |
| `color` | str | `color` / `gray` / `bw` |
| `jpeg_quality` | int | 1–95 |
| `skew` | float | 0–5 (도) |
| `fold` | str | `none` / `half` / `trifold` |
| `fold_strength` | float | 0–1 |
| `noise` | float | 0–1 |
| `paper` | float | 0–1 |
| `edge_shadow` | float | 0–1 |
| `unevenness` | float | 0–1 |
| `blur` | float | 0–3 (px, 200 DPI 기준) |

### 프리셋

| 필드 | light | normal | heavy |
|---|---|---|---|
| 상정 상황 | 좋은 스캐너, 새 종이 | 사무실 복합기 | 오래된 문서, 낡은 스캐너 |
| `dpi` | 200 | 200 | 150 |
| `color` | color | color | gray |
| `jpeg_quality` | 85 | 75 | 60 |
| `skew` | 0.3 | 0.7 | 1.5 |
| `fold` | none | none | trifold |
| `fold_strength` | 0.5 | 0.5 | 0.7 |
| `noise` | 0.15 | 0.3 | 0.55 |
| `paper` | 0.1 | 0.25 | 0.5 |
| `edge_shadow` | 0.1 | 0.25 | 0.5 |
| `unevenness` | 0.1 | 0.2 | 0.4 |
| `blur` | 0.3 | 0.6 | 1.0 |

- 기본 색상이 `color`인 이유: `gray`는 붉은 도장·직인을 지운다.
- 위 수치는 출발값이다. 구현 중 `examples/` 샘플을 보고 조정하며, 조정 결과를 이 표에 반영한다.

## 6. CLI

```
scannizer INPUT [-o OUTPUT] [--preset {light,normal,heavy}] [--seed N]
          [--dpi N] [--color {color,gray,bw}] [--jpeg-quality N]
          [--skew DEG] [--fold {none,half,trifold}] [--fold-strength X]
          [--noise X] [--paper X] [--edge-shadow X] [--unevenness X] [--blur X]
          [--version]
```

- `-o` 생략 시 입력과 같은 디렉터리에 `<이름>_scanned.pdf`로 저장한다.
- 지정하지 않은 옵션은 프리셋 값을 따른다.
- argparse로 구현한다(추가 의존성 없음). `pyproject.toml`의 `[project.scripts]`에 `scannizer = "scannizer.cli:main"`으로 등록한다.

## 7. 오류 처리

| 상황 | 라이브러리 | CLI |
|---|---|---|
| 입력 파일 없음, PDF가 아님, 손상됨 | `ScannizerError` | stderr 한 줄 메시지, 종료 코드 1 |
| 페이지가 0개 | `ScannizerError` | 동일 |
| 암호화된 PDF | `ScannizerError` (미지원 안내) | 동일 |
| 출력 경로가 입력과 같음 | `ScannizerError` | 동일 |
| 옵션 값 범위 초과, 알 수 없는 프리셋 | `ValueError` | argparse 오류, 종료 코드 2 |
| 알 수 없는 override 키 | `TypeError` | 해당 없음 |

- 입력과 다른 경로의 기존 출력 파일은 덮어쓴다.
- CLI는 `ScannizerError`에 대해 트레이스백을 출력하지 않는다.

## 8. 모듈 구성

```
scannizer/
  pyproject.toml
  README.md
  LICENSE                 MIT
  src/scannizer/
    __init__.py           scan, ScanOptions, ScannizerError 공개
    cli.py                인자 파싱 → scan() 호출
    pipeline.py           scan() 구현: 페이지 순회, 효과 순서, 원자적 저장
    raster.py             PDF 열기·검증, 페이지 → RGB 배열
    assemble.py           JPEG 바이트 목록 → PDF
    options.py            ScanOptions, 범위 검증
    presets.py            light / normal / heavy
    errors.py             ScannizerError
    effects/
      paper.py            종이 질감
      fold.py             접힘
      geometry.py         기울어짐
      optics.py           가장자리 그림자, 밝기 불균일, 블러
      noise.py            노이즈
      color.py            색상 모드
  tests/
    effects/              효과별 단위 테스트
    test_pipeline.py
    test_cli.py
    test_options.py
  examples/
    make_samples.py       프리셋별 샘플 PDF 생성 (시각 검수용)
```

경계:

- `effects/*`는 배열과 난수 생성기만 안다. PDF, 파일, 프리셋을 모른다.
- `raster.py`와 `assemble.py`만 pypdfium2를 쓴다.
- `pipeline.py`만 효과 순서와 옵션 → 효과 인자 매핑을 안다.
- `cli.py`는 `scan()` 외의 내부 모듈을 호출하지 않는다.

## 9. 의존성과 환경

| 패키지 | 용도 | 라이선스 |
|---|---|---|
| pypdfium2 | PDF 래스터화, JPEG 임베드 PDF 생성 | Apache-2.0 / BSD-3-Clause |
| numpy | 배열 연산, 난수 | BSD-3-Clause |
| opencv-python-headless | 회전·블러·리사이즈, JPEG 인코딩 | Apache-2.0 |

- Python 3.10 이상
- 빌드: hatchling, 린트: ruff, 테스트: pytest
- PyMuPDF는 AGPL이라 쓰지 않는다.

## 10. 테스트

**효과 단위 (효과마다)**

- 출력의 shape·dtype이 규칙과 일치
- 강도 0이면 입력과 동일
- 같은 시드면 동일, 다른 시드면 다름
- 강도를 올리면 입력과의 차이가 커짐
- 효과별 속성: 기울어짐 각도가 범위 안, 접힘선 수가 패턴과 일치, `gray` 출력이 단일 채널, `bw` 출력 값이 0과 255뿐

**파이프라인 통합** (테스트 안에서 pypdfium2로 텍스트가 있는 작은 PDF 생성)

- 페이지 수 유지, 페이지 크기 유지(±1pt)
- 출력에 텍스트 레이어 없음
- 같은 시드 → 렌더링한 페이지 픽셀 동일
- 크기가 서로 다른 페이지가 섞인 PDF 처리
- 오류 표의 각 상황에서 지정된 예외 발생, 실패 시 출력 파일이 남지 않음

**옵션·CLI**

- 범위 밖 값, 알 수 없는 프리셋·키 거부
- override가 프리셋 값을 덮어씀
- 기본 출력 파일명, 종료 코드 0 / 1 / 2

**시각 검수**

`examples/make_samples.py`가 샘플 문서를 프리셋별로 변환한다. 자동 테스트에 포함하지 않는다.

## 11. 배포 전 확인 사항

- PyPI에서 `scannizer` 이름 사용 가능 여부
