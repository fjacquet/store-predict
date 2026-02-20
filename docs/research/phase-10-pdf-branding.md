# Phase 10: PDF Branding - Research

**Researched:** 2026-02-20
**Domain:** ReportLab image embedding, Pillow image preprocessing, NiceGUI file upload, logo validation
**Confidence:** HIGH

## Summary

Phase 10 adds Dell partner branding and an optional custom company logo to the existing one-page PDF report. The existing `_draw_header` canvas callback is the correct integration point — it draws directly on the ReportLab canvas outside the Platypus story flow, so adding images there does not consume page vertical space. PNG transparency is the critical risk: Pillow preprocessing to RGBA PNG before passing bytes to ReportLab handles all edge cases reliably.

## Key Findings

### canvas.drawImage via ImageReader(BytesIO)

`canvas.drawImage()` accepts an `ImageReader` wrapping a `BytesIO` object. This is the correct in-memory pattern — no temp files needed. Use `mask='auto'` to preserve PNG transparency in the PDF.

```python
from reportlab.lib.utils import ImageReader

reader = ImageReader(BytesIO(logo_bytes))
canvas.drawImage(
    reader,
    x=width - 90, y=height - 43,
    width=80, height=36,
    mask='auto',
    preserveAspectRatio=True,
)
```

### Pillow Preprocessing to RGBA PNG

Always normalize any incoming logo bytes to RGBA PNG via Pillow before passing to ReportLab. This handles palette-mode (`P`/`PA`) images that would otherwise render with a black background under `mask='auto'`.

```python
from PIL import Image as PilImage

def _preprocess_logo(raw_bytes: bytes) -> bytes:
    with PilImage.open(BytesIO(raw_bytes)) as img:
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
```

Apply this to both the static Dell logo (at module load) and user-uploaded logos.

### Magic-Byte Logo Validation

Validate uploaded logos by magic bytes before Pillow processing. Reject files over 200 KB to keep `app.storage.tab` safe (JSON-backed, per-tab storage).

```python
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"
_MAX_LOGO_BYTES = 200 * 1024

def validate_logo(content: bytes, filename: str) -> None:
    if len(content) > _MAX_LOGO_BYTES:
        raise IngestionError("Logo file exceeds 200 KB limit.")
    if not (content[:8] == _PNG_MAGIC or content[:3] == _JPEG_MAGIC):
        raise IngestionError("Logo must be PNG or JPEG.")
```

### Static Dell Logo as Package Data

Store the Dell logo under `src/store_predict/data/dell_logo.png` and load it via `importlib.resources` or a `Path(__file__).parent` constant in `config.py`. Preprocess once at import time.

### Header Bar Geometry Constraints

The existing header bar is 50 points tall. Logos must fit within ~40 points of usable height (with top/bottom padding). Place the Dell logo right-aligned and the company logo left-aligned inside the bar. Text position shifts right when a company logo is present.

### base64 for Tab Storage

Store user-uploaded logo bytes as a base64 string in `app.storage.tab`. Decode at PDF generation time. Keep logos under 200 KB to avoid hitting tab storage limits.

```python
import base64
app.storage.tab["company_logo_b64"] = base64.b64encode(logo_bytes).decode()
# At PDF generation:
raw = base64.b64decode(app.storage.tab.get("company_logo_b64", ""))
```

## Anti-Patterns

- **Using `mask='auto'` without converting palette-mode images:** `mask='auto'` handles RGBA correctly but fails for mode-`P` images — they render with a black background. Always convert to RGBA via Pillow first.
- **Using the Platypus `Image` flowable for header logos:** The `Image` flowable lives in the story flow and consumes page vertical space, risking a two-page report. Use `canvas.drawImage()` inside the `_draw_header` callback instead.
- **Storing large logos in tab storage:** `app.storage.tab` is JSON-backed per-tab storage. Logos over 200 KB inflate storage and may cause serialization slowdowns.

## Dependencies

| Package | Version | Notes |
|---------|---------|-------|
| Pillow | 12.1.1 (installed) | Already in `.venv`; add `"pillow>=12.1.1"` to `pyproject.toml` dependencies |
| ReportLab | 4.4.10 (installed) | No version change needed |
