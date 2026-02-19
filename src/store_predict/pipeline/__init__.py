"""Pipeline: pure business logic for VM ingestion, classification, and calculation."""

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
    calculate,
)
from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.ingestion import detect_format, ingest_file
from store_predict.pipeline.models import FileFormat

__all__ = [
    "CalculationSummary",
    "FileFormat",
    "IngestionError",
    "VMCalculation",
    "WorkloadGroupResult",
    "calculate",
    "detect_format",
    "ingest_file",
]
