# Phase 10: PDF Branding - Research

**Researched:** 2026-02-20
**Domain:** ReportLab image embedding, Pillow image preprocessing, NiceGUI file upload, logo validation
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BRAND-01 | Dell partner logo displayed in PDF report header (static asset shipped with app) | canvas.drawImage() in `_draw_header` callback; ImageReader(BytesIO) pattern; logo stored as package data under `src/store_predict/data/` |
| BRAND-02 | User can upload a custom company logo (PNG/JPEG) via UI | NiceGUI `ui.upload` with `on_upload` handler; `e.content.read()` gives raw bytes; store base64 in `app.storage.tab` |
| BRAND-03 | Uploaded logo embedded in PDF report alongside Dell logo | Pass logo bytes through `generate_report_pdf()` via optional kwargs; Pillow-preprocess then ImageReader; `canvas.drawImage()` in header callback |
| BRAND-04 | Logo images validated (format, dimensions) and scaled to fit without breaking one-page layout | Magic-byte format check (PNG: `\x89PNG`, JPEG: `\xff\xd8\xff`); Pillow `.size` for dimension limits; `canvas.drawImage(width=W, height=H)` for scaling; header bar is 50pt, logo max ~40pt tall |
| BRAND-05 | PNG transparency handled correctly (no black background in PDF) | Pillow: convert mode P/PA → RGBA, composite on white for PDF embedding; OR use `mask='auto'` on `canvas.drawImage`; the latter is simpler but P mode must still be converted first |
</phase_requirements>

---

## Summary

Phase 10 adds Dell partner branding and optional custom company logo to the existing one-page PDF report. The existing `_draw_header` callback draws directly on the ReportLab canvas — this is the correct integration point for logos. The header bar is 50 points tall with text at y = height-35 and project name at y = height-68; logos must fit within the 50pt bar height (≈40pt usable) to avoid pushing content down.

The standard pattern is: store the Dell logo as a package data file (`src/store_predict/data/dell_logo.png`), load it via `importlib.resources` or a path constant in `config.py`, and pass it to `canvas.drawImage()` via `ImageReader(BytesIO(logo_bytes))` with `mask='auto'` to preserve transparency. For user-uploaded logos the same flow applies, but raw bytes come from `app.storage.tab` (stored as base64 string) and must be Pillow-preprocessed before PDF embedding.

PNG transparency is the critical risk: ReportLab's `mask='auto'` handles RGBA PNGs correctly but palette-mode (`P`) PNGs with transparency must first be converted to `RGBA` via Pillow (`img.convert("RGBA")`). The safest pipeline is: Pillow open → convert to RGBA → save to fresh BytesIO as PNG → pass to ImageReader. Pillow 12.1.1 is already installed in `.venv`.

**Primary recommendation:** Implement a `_preprocess_logo(raw_bytes: bytes) -> bytes` helper in `pdf_report.py` that always converts any uploaded image to RGBA PNG via Pillow, then feeds it to ReportLab via ImageReader. This single function handles all mode edge-cases and avoids black-background issues.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ReportLab | 4.4.10 (installed) | PDF generation — canvas.drawImage, ImageReader | Already in project; the only PDF library used |
| Pillow | 12.1.1 (installed) | Image preprocessing — mode conversion, transparency, resize | Required for P→RGBA, validation, dimension checks |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `reportlab.lib.utils.ImageReader` | bundled with ReportLab | Wraps BytesIO for canvas.drawImage | Every time an in-memory image must be drawn on canvas |
| `importlib.resources` | stdlib | Load package-data logo file as bytes | For the static Dell logo shipped with the app |
| `base64` (stdlib) | stdlib | Encode/decode logo bytes for app.storage.tab | To safely serialize binary in JSON-backed tab storage |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Storing logo as base64 in tab storage | Temporary file on disk | Tab storage is simpler, no file cleanup; watch size limit (keep logos < 200 KB) |
| Pillow preprocessing all images | `mask='auto'` only | `mask='auto'` alone fails on mode-P PNGs; Pillow preprocessing is universal |
| ReportLab Platypus `Image` flowable in story | canvas.drawImage in header callback | Header callback runs outside story flow; `Image` flowable would consume page vertical space, risking page 2 |

**Installation:**
Pillow is already installed. No new `pip install` needed. Add to `pyproject.toml` dependencies:
```bash
uv pip install "pillow>=12.1.1"
# then add to pyproject.toml [project] dependencies:
# "pillow>=12.1.1",
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/store_predict/
├── data/
│   ├── DRR.csv                   # existing
│   └── dell_logo.png             # NEW: static Dell partner logo (PNG, ≤200KB)
├── services/
│   └── pdf_report.py             # MODIFIED: add logo params + _preprocess_logo helper
└── ui/
    └── pages/
        └── report.py             # MODIFIED: logo upload UI + pass to generate_report_pdf
```

### Pattern 1: Logo In Header Callback (canvas.drawImage)

**What:** Draw logo PNG directly on the canvas inside `_draw_header`. The callback already saves/restores canvas state. Pass logo bytes as optional parameter via closure capture.
**When to use:** Any time image must appear outside Platypus story flow (header, footer, watermark).

```python
# Source: ReportLab docs ch2_graphics + reportlab-users mailing list
from io import BytesIO
from reportlab.lib.utils import ImageReader

def _draw_header(
    canvas: Canvas,
    doc: SimpleDocTemplate,
    project_name: str,
    report_title: str,
    dell_logo_bytes: bytes | None = None,
    company_logo_bytes: bytes | None = None,
) -> None:
    canvas.saveState()
    width, height = A4
    bar_height = 50

    # Draw dark blue bar
    canvas.setFillColor(_BRAND_BLUE)
    canvas.rect(0, height - bar_height, width, bar_height, fill=1, stroke=0)

    # Dell logo: right-aligned inside bar
    if dell_logo_bytes:
        reader = ImageReader(BytesIO(dell_logo_bytes))
        logo_h = 36  # points (~12.7mm), fits in 50pt bar with padding
        logo_w = 80  # scale width — actual ratio enforced by Pillow preprocessing
        canvas.drawImage(
            reader,
            width - logo_w - 10,   # right margin
            height - bar_height + 7,  # vertical center
            width=logo_w,
            height=logo_h,
            mask='auto',
            preserveAspectRatio=True,
        )

    # Company logo: left of Dell logo or separate position
    if company_logo_bytes:
        reader = ImageReader(BytesIO(company_logo_bytes))
        canvas.drawImage(
            reader,
            10,
            height - bar_height + 7,
            width=80,
            height=36,
            mask='auto',
            preserveAspectRatio=True,
        )

    # Title text (shift right if company logo present)
    x_title = 100 if company_logo_bytes else 20 * mm
    canvas.setFillColor(colors.white)
    canvas.setFont("VeraBd", 18)
    canvas.drawString(x_title, height - 35, report_title)

    # Project name + date below bar
    canvas.setFillColor(colors.black)
    canvas.setFont("Vera", 11)
    date_str = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    canvas.drawString(20 * mm, height - bar_height - 18, f"{project_name}  |  {date_str}")

    canvas.restoreState()
```

### Pattern 2: PNG Transparency Preprocessing (Pillow)

**What:** Before passing any logo bytes to ReportLab, normalize the image to RGBA PNG via Pillow. This handles palette-mode P, LA, CMYK, and any other edge case.
**When to use:** Always — applied to both Dell static logo at load time and user-uploaded logos.

```python
# Source: Pillow 12.1.1 docs (pillow.readthedocs.io/en/stable/reference/Image.html)
from PIL import Image as PilImage
from io import BytesIO

def _preprocess_logo(raw_bytes: bytes) -> bytes:
    """Normalize any image to RGBA PNG for safe ReportLab embedding.

    Converts palette-mode (P/PA) images to RGBA to prevent black
    backgrounds. Composites on white only if caller explicitly needs RGB,
    but RGBA+mask='auto' is preferred to keep transparency in PDF.
    """
    with PilImage.open(BytesIO(raw_bytes)) as img:
        if img.mode in ("P", "PA"):
            img = img.convert("RGBA")
        elif img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
```

### Pattern 3: Logo Validation

**What:** Check magic bytes for format, Pillow for dimensions. Reject oversized or wrong-format files.
**When to use:** In UI handler before storing to `app.storage.tab`. Also re-validate in `generate_report_pdf` as a safety net.

```python
# Magic bytes validation (no external library needed)
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_MAX_LOGO_BYTES = 200 * 1024       # 200 KB — keeps tab storage safe
_MAX_LOGO_DIMENSION = 2000         # pixels — reject absurd resolution

def validate_logo(content: bytes, filename: str) -> None:
    """Validate logo file format and dimensions.

    Raises IngestionError for unsupported format, oversized file,
    or unreasonable image dimensions.
    """
    from store_predict.pipeline.errors import IngestionError

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("png", "jpg", "jpeg"):
        raise IngestionError(f"Logo must be PNG or JPEG, got .{ext}")
    if len(content) > _MAX_LOGO_BYTES:
        raise IngestionError(f"Logo file too large (max 200 KB, got {len(content)//1024} KB)")
    if ext == "png" and not content.startswith(_PNG_MAGIC):
        raise IngestionError("File does not appear to be a valid PNG image")
    if ext in ("jpg", "jpeg") and not content.startswith(_JPEG_MAGIC):
        raise IngestionError("File does not appear to be a valid JPEG image")

    # Dimension check via Pillow
    from PIL import Image as PilImage
    with PilImage.open(BytesIO(content)) as img:
        w, h = img.size
        if w > _MAX_LOGO_DIMENSION or h > _MAX_LOGO_DIMENSION:
            raise IngestionError(f"Logo too large ({w}x{h}px, max {_MAX_LOGO_DIMENSION}px)")
```

### Pattern 4: Storing Logo in Tab Storage

**What:** Encode logo bytes to base64 string for JSON-serializable tab storage.
**When to use:** In the NiceGUI upload handler on the report page.

```python
# Source: NiceGUI docs (nicegui.io/documentation/upload) + storage discussion #3052
import base64
from nicegui import app, ui

async def _handle_logo_upload(e: object) -> None:
    content: bytes = e.content.read()  # type: ignore[attr-defined]
    filename: str = e.name  # type: ignore[attr-defined]
    try:
        validate_logo(content, filename)
        app.storage.tab["company_logo_b64"] = base64.b64encode(content).decode("ascii")
        ui.notify(t("report.logo_uploaded"), type="positive")
    except Exception as exc:
        ui.notify(str(exc), type="negative")
```

### Pattern 5: Backwards-Compatible generate_report_pdf Signature

**What:** Add optional `company_logo_bytes` and `dell_logo_bytes` kwargs. Existing callers pass nothing and get identical behavior.
**When to use:** Always — no breaking changes to existing tests.

```python
def generate_report_pdf(
    summary: CalculationSummary,
    project_name: str,
    locale: str = "fr",
    dell_logo_bytes: bytes | None = None,
    company_logo_bytes: bytes | None = None,
) -> bytes:
    ...
    dell_logo_preprocessed = _preprocess_logo(dell_logo_bytes) if dell_logo_bytes else None
    company_logo_preprocessed = _preprocess_logo(company_logo_bytes) if company_logo_bytes else None

    def on_first_page(canvas: Canvas, doc: SimpleDocTemplate) -> None:
        _draw_header(
            canvas, doc, project_name, report_title,
            dell_logo_bytes=dell_logo_preprocessed,
            company_logo_bytes=company_logo_preprocessed,
        )
    ...
```

### Anti-Patterns to Avoid

- **Platypus Image flowable in story:** Adding logos as `Image(...)` in the story list adds them to the vertical content flow, risking page 2 overflow. Logos must be in the header callback only.
- **Storing raw bytes in tab storage:** `app.storage.tab` is JSON-backed; store base64 string, not raw bytes.
- **Skipping Pillow preprocessing:** Calling `ImageReader(BytesIO(raw_bytes))` without Pillow preprocessing will silently render palette-mode PNGs with black backgrounds in the PDF.
- **Using canvas.drawInlineImage:** Deprecated; use `canvas.drawImage` which implements caching.
- **Hardcoding logo path as absolute filesystem path:** Use `importlib.resources` or a config path constant relative to the package; absolute paths break Docker builds.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PNG mode conversion | Custom pixel-level loop | `PIL.Image.convert("RGBA")` | Handles all mode variants (P, PA, LA, CMYK, L) correctly; palette transparency edge-cases are complex |
| Aspect ratio scaling | Manual width/height math | `canvas.drawImage(..., preserveAspectRatio=True)` | ReportLab handles the math correctly; manual math introduces rounding bugs |
| Image format detection | Extension-only check | Magic bytes + Pillow open | Extensions can be spoofed; Pillow open will fail on invalid image data |
| Base64 encoding | Manual byte encoding | `base64.b64encode` / `b64decode` | stdlib; no third-party dep needed |

**Key insight:** The combination of Pillow preprocessing + `mask='auto'` on `canvas.drawImage` eliminates every known transparency issue. Any custom solution for PNG transparency will miss edge cases (indexed palette, 1-bit alpha, CMYK, etc.).

---

## Common Pitfalls

### Pitfall 1: PNG Mode P → Black Background
**What goes wrong:** A palette-indexed PNG with transparency is passed directly to ReportLab. The alpha channel is ignored; transparent regions render as black.
**Why it happens:** ReportLab's `mask='auto'` only handles RGBA PNGs; mode P stores transparency in the palette info dict, not in a dedicated channel.
**How to avoid:** Always run `_preprocess_logo()` which converts mode P to RGBA before handing bytes to `ImageReader`.
**Warning signs:** Logo appears with solid black or colored background in generated PDF.

### Pitfall 2: Logo Pushes Content to Page 2
**What goes wrong:** Logo image placed in story (as Platypus `Image` flowable) occupies vertical space, causing the workload table to overflow to a second page.
**Why it happens:** Platypus lays out story elements sequentially; an Image flowable at the top consumes `topMargin` space and reduces the writable area.
**How to avoid:** Draw logos exclusively in `_draw_header` via `canvas.drawImage`. Never add logos to the `story` list.
**Warning signs:** PDF grows from 1 page to 2 pages in tests.

### Pitfall 3: Tab Storage Serialization Error
**What goes wrong:** `app.storage.tab["company_logo"] = raw_bytes` raises a serialization error at runtime.
**Why it happens:** `app.storage.tab` is a persistent dict backed by JSON. Python `bytes` are not JSON-serializable.
**How to avoid:** Store `base64.b64encode(bytes).decode("ascii")` string; decode back with `base64.b64decode(s)` before use.
**Warning signs:** NiceGUI raises `TypeError: Object of type bytes is not JSON serializable`.

### Pitfall 4: Dell Logo Not Found in Docker
**What goes wrong:** `open("dell_logo.png")` works locally but raises `FileNotFoundError` in Docker.
**Why it happens:** Relative filesystem paths don't survive Docker `COPY` and working-directory changes.
**How to avoid:** Store logo under `src/store_predict/data/`, declare in `pyproject.toml` `[tool.setuptools.package-data]`, access via `importlib.resources` or a `Path(__file__).parent / "data" / "dell_logo.png"` constant in `config.py`.
**Warning signs:** PDF generates fine in dev but `FileNotFoundError` in container.

### Pitfall 5: Header Layout Breaks With Both Logos
**What goes wrong:** Two logos + title text all compete for the 50pt header bar, causing overlap or clipped text.
**Why it happens:** Current `_draw_header` draws title at a fixed x coordinate; with a company logo at x=10 the text overlaps.
**How to avoid:** When company logo is present, shift the title x-coordinate right (e.g., x_title = 100 when logo present, else 20mm). Test by generating a PDF with both logos and measuring pixel positions.
**Warning signs:** Title text overlaps or is hidden by company logo in output PDF.

---

## Code Examples

Verified patterns from official sources:

### Load Static Dell Logo (package data)

```python
# Source: Python stdlib importlib.resources (docs.python.org)
from importlib.resources import files
import store_predict.data as _data_pkg

def _load_dell_logo() -> bytes | None:
    """Load Dell partner logo shipped as package data."""
    try:
        logo_ref = files(_data_pkg).joinpath("dell_logo.png")
        return logo_ref.read_bytes()
    except (FileNotFoundError, ModuleNotFoundError):
        return None  # graceful degradation — logo is optional at runtime
```

Alternatively (simpler, already used in codebase pattern):
```python
# Source: config.py pattern already in use for DRR_CSV_PATH
DELL_LOGO_PATH = Path(__file__).resolve().parent / "data" / "dell_logo.png"

def _load_dell_logo() -> bytes | None:
    try:
        return DELL_LOGO_PATH.read_bytes()
    except FileNotFoundError:
        return None
```

### Full Preprocessing Pipeline

```python
# Source: Pillow 12.1.1 docs + ReportLab reportlab-users mailing list
from PIL import Image as PilImage
from io import BytesIO
from reportlab.lib.utils import ImageReader

def _preprocess_logo(raw_bytes: bytes) -> bytes:
    """Normalize to RGBA PNG for black-background-safe ReportLab embedding."""
    with PilImage.open(BytesIO(raw_bytes)) as img:
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

# Usage in _draw_header:
reader = ImageReader(BytesIO(_preprocess_logo(logo_bytes)))
canvas.drawImage(reader, x, y, width=w, height=h, mask='auto', preserveAspectRatio=True)
```

### Logo Upload UI on Report Page

```python
# Source: NiceGUI docs ui.upload (nicegui.io/documentation/upload)
# NiceGUI 3.4+ pattern — e.content is SpooledTemporaryFile, e.name is filename
import base64
from nicegui import app, ui

def _build_logo_upload_section() -> None:
    ui.label(t("report.upload_logo")).classes("text-sm font-semibold")
    ui.upload(
        label=t("report.logo_upload_label"),
        on_upload=_handle_logo_upload,
        auto_upload=True,
        max_file_size=200_000,   # 200 KB hard limit
    ).props('accept=".png,.jpg,.jpeg"').classes("w-full")

async def _handle_logo_upload(e: object) -> None:
    content: bytes = e.content.read()   # type: ignore[attr-defined]
    filename: str = e.name              # type: ignore[attr-defined]
    try:
        validate_logo(content, filename)
        app.storage.tab["company_logo_b64"] = base64.b64encode(content).decode("ascii")
        ui.notify(t("report.logo_uploaded"), type="positive")
    except Exception as exc:
        ui.notify(str(exc), type="negative")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `canvas.drawInlineImage` | `canvas.drawImage` + ImageReader | ReportLab 2.x | Caching, no duplicate image data in PDF |
| PIL Image floats | Pillow `Image.convert("RGBA")` | Pillow 8.x (PILLOW fork renamed) | Mode conversion is the correct API; `.point()` hacks obsolete |
| `mask=[r1,r2,g1,g2,b1,b2]` for transparency | `mask='auto'` | ReportLab 3.x | Auto-detects PNG alpha channel |

**Deprecated/outdated:**
- `canvas.drawInlineImage`: Still works but no caching; avoid in favor of `drawImage`.
- PIL `Image.save(fp, "PDF")` for embedding: This saves a separate PDF, not what we need; use `ImageReader` + `drawImage` instead.

---

## Open Questions

1. **Dell logo asset availability**
   - What we know: No logo exists yet in the repo (`src/store_predict/data/` has only `DRR.csv`)
   - What's unclear: Whether a Dell partner logo PNG file has been sourced, and what its dimensions/mode are
   - Recommendation: Plan must include a task to obtain/create a placeholder Dell logo PNG (~80x36pt at 96dpi = 107x48px). If not yet sourced, use a placeholder during development. Real logo can be dropped in later without code change.

2. **Header layout with both logos present**
   - What we know: Current header bar is 50pt tall; title text at x=20mm; project name below bar
   - What's unclear: Exact pixel budget when both Dell logo (right-aligned) and company logo (left-aligned) are present alongside title text
   - Recommendation: Reserve x=10..100 for company logo, x=width-100..width-10 for Dell logo, shift title text to center. Empirically verify with a test PDF that text doesn't collide.

3. **`app.storage.tab` size in production**
   - What we know: Tab storage is JSON-backed; browser storage is typically 5-10MB; 200KB base64 logo ≈ 267KB string
   - What's unclear: NiceGUI's server-side tab storage uses in-memory dict (no browser cookie), so browser 4KB cookie limit doesn't apply. The limit is effectively Python process memory.
   - Recommendation: Enforce 200KB max upload in UI (`max_file_size=200_000`). Document this limit. No further investigation needed.

---

## Sources

### Primary (HIGH confidence)
- ReportLab 4.4.10 (installed in .venv) — verified version via `reportlab.__version__`
- [ReportLab ch2_graphics docs](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/) — `canvas.drawImage` signature, `mask='auto'`, `ImageReader`, `preserveAspectRatio`
- [Pillow 12.1.1 docs — Image.html](https://pillow.readthedocs.io/en/stable/reference/Image.html) — `Image.open`, `.convert()`, `.size`, `.save()`
- [Pillow 12.1.1 docs — concepts.html](https://pillow.readthedocs.io/en/stable/handbook/concepts.html) — P, RGBA mode descriptions

### Secondary (MEDIUM confidence)
- [NiceGUI storage docs](https://nicegui.io/documentation/storage) — `app.storage.tab` data types, JSON serialization requirement
- [NiceGUI upload docs](https://nicegui.io/documentation/upload) — `UploadEventArguments.content.read()`, `e.name`
- [reportlab-users: Transparent PNG](https://groups.google.com/g/reportlab-users/c/ldbVVQLjIXU) — `mask='auto'` for RGBA PNGs confirmed
- Direct codebase inspection: `src/store_predict/services/pdf_report.py` — existing `_draw_header`, `generate_report_pdf` signature, header bar geometry (50pt, y positions)

### Tertiary (LOW confidence)
- [NiceGUI discussion #3052](https://github.com/zauberzeug/nicegui/discussions/3052) — `app.storage.tab` patterns (unverified exact behavior of large string storage)
- [reportlab-users: ImageReader BytesIO pattern](https://python.hotexamples.com/examples/reportlab.lib.utils/ImageReader/-/python-imagereader-class-examples.html) — corroborates BytesIO + ImageReader pattern but single source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both libraries installed and verified in .venv
- Architecture patterns: HIGH — directly derived from reading existing `pdf_report.py` + official ReportLab/Pillow docs
- Pitfalls: HIGH — transparent PNG black background is a well-documented ReportLab issue confirmed by multiple sources; tab storage serialization is observable from NiceGUI source
- Open questions: MEDIUM — Dell logo asset and header layout require empirical testing

**Research date:** 2026-02-20
**Valid until:** 2026-05-20 (stable libraries; ReportLab and Pillow APIs are stable)
