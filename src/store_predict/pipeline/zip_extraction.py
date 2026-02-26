"""Extract xlsx data from a ZIP archive for the sizing pipeline.

Handles LiveOptics exports (canonical ``LiveOptics_<id>_VMWARE_<DD>_<MM>_<YYYY>.xlsx``
pattern) and any other ZIP wrapping a single xlsx file (e.g. RVTools zips or
non-standard LiveOptics exports). The canonical pattern is tried first; if no
match is found, the first xlsx member in the archive is used instead.
"""

from __future__ import annotations

import io
import re
import zipfile

from store_predict.pipeline.errors import IngestionError

# Maximum total uncompressed size across all ZIP members (100 MB).
# Checked against the central directory only — no extraction needed.
_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024

_LIVEOPTICS_PATTERN = re.compile(r"LiveOptics_\d+_VMWARE_\d{2}_\d{2}_\d{4}\.xlsx", re.IGNORECASE)


def extract_liveoptics_from_zip(content: bytes) -> tuple[bytes, str]:
    """Extract the LiveOptics xlsx from a ZIP archive.

    Args:
        content: Raw bytes of the uploaded .zip file.

    Returns:
        A ``(xlsx_bytes, filename)`` tuple where *filename* is the matched
        member name (e.g. ``LiveOptics_123_VMWARE_01_01_2025.xlsx``).

    Raises:
        IngestionError: If the archive is invalid, exceeds the uncompressed
            size limit, or contains no matching LiveOptics file.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise IngestionError("Uploaded .zip file is not a valid ZIP archive") from exc

    # Zip bomb guard — reads central directory only, no extraction yet.
    total_uncompressed = sum(info.file_size for info in zf.infolist())
    if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
        raise IngestionError(
            f"ZIP archive uncompressed content exceeds the {_MAX_UNCOMPRESSED_BYTES // (1024 * 1024)} MB limit"
        )

    names = zf.namelist()

    # Primary: canonical LiveOptics pattern.
    matches = [name for name in names if _LIVEOPTICS_PATTERN.search(name)]

    # Fallback: any xlsx (handles RVTools-in-zip, non-standard LiveOptics exports, etc.)
    if not matches:
        matches = [name for name in names if name.lower().endswith(".xlsx")]

    if not matches:
        raise IngestionError(
            "No xlsx file found in ZIP. Please upload a ZIP archive containing a LiveOptics or RVTools .xlsx file."
        )

    # Take first match if multiple (documented: first-match wins).
    member_name = matches[0]
    xlsx_bytes = zf.read(member_name)
    return xlsx_bytes, member_name
