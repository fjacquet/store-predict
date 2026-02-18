"""Pipeline: pure business logic for VM ingestion, classification, and calculation."""

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import detect_format, ingest_file
from store_predict.pipeline.models import FileFormat

__all__ = [
    "FileFormat",
    "IngestionError",
    "detect_format",
    "ingest_file",
]
