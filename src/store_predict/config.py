"""Project paths and default configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DRR_CSV_PATH = SAMPLES_DIR / "DRR.csv"

DEFAULT_DRR = 5.0
APP_TITLE = "StorePredict"
APP_PORT = 8080

# Company prefix patterns for VM name stripping.
# List of regex patterns anchored to start of VM name, e.g. [r"^ACME[-_]", r"^CORP[-_]"].
# When non-empty, the classifier will strip matching prefixes before pattern matching.
COMPANY_PREFIX_PATTERNS: list[str] = []

# Performance columns extracted from LiveOptics VM Performance sheet.
# Used as a reference list for downstream consumers (UI, reports).
PERFORMANCE_COLUMNS: list[str] = [
    "peak_iops",
    "avg_iops",
    "peak_throughput_mbs",
    "avg_throughput_mbs",
    "peak_latency_ms",
    "avg_read_latency_ms",
    "avg_write_latency_ms",
    "iops_8k_equivalent",
]
