#!/usr/bin/env python
"""Ad-hoc bucket-distribution dump for a real customer file.

Usage:
    python scripts/classify_customer_dump.py <path-to-rvtools-or-liveoptics>

Read-only — parses the file, classifies VMs, and prints subcategory + confidence
counts. Useful for pre-sales spot-checks against real customer data without
relying on the UI.
"""

from __future__ import annotations

import sys
from pathlib import Path

from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)
from store_predict.pipeline.ingestion import ingest_file


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    path = Path(argv[1]).expanduser()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    print(f"Parsing {path.name} ...")
    df = ingest_file(path)
    print(f"  -> {len(df)} VMs after template/powerstate filtering")

    registry = RuleRegistry(build_default_rules())
    res = classify_dataframe(df, registry)

    confidence_counts = res["classification_confidence"].value_counts()
    print("\nConfidence distribution:")
    for k, v in confidence_counts.items():
        print(f"  {k:<14} {v:>5}")

    print("\nSubcategory distribution:")
    for sub, count in res["workload_subcategory"].value_counts().items():
        print(f"  {str(sub)[:60]:<62} {count:>5}")

    print("\nCategory totals:")
    for cat, count in res["workload_category"].value_counts().items():
        print(f"  {cat!s:<30} {count:>5}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
