"""Project paths and default configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = PROJECT_ROOT / "samples"
DRR_CSV_PATH = SAMPLES_DIR / "DRR.csv"

DEFAULT_DRR = 5.0
APP_TITLE = "StorePredict"
APP_PORT = 8080
