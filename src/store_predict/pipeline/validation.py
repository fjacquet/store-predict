"""Server-side file upload validation.

Validates uploaded files by extension and magic bytes before pipeline processing.
Rejects files that are not genuine .xlsx or .csv to prevent malicious uploads.
"""

from __future__ import annotations

from store_predict.pipeline.errors import IngestionError

# ZIP (and hence .xlsx) magic bytes
_XLSX_MAGIC = b"PK\x03\x04"


def validate_upload(content: bytes, filename: str) -> None:
    """Validate uploaded file by extension and content inspection.

    Args:
        content: Raw file bytes.
        filename: Original filename from the upload.

    Raises:
        IngestionError: If the file extension is unsupported or content
            does not match the expected format.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("xlsx", "csv"):
        raise IngestionError(f"Unsupported file type: .{ext}. Only .xlsx and .csv files are accepted.")

    if ext == "xlsx" and (len(content) < 4 or content[:4] != _XLSX_MAGIC):
        raise IngestionError("File does not appear to be a valid .xlsx file")

    if ext == "csv":
        try:
            content[:1024].decode("utf-8")
        except UnicodeDecodeError as err:
            raise IngestionError("File does not appear to be a valid CSV file") from err
