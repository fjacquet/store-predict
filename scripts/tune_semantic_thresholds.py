# scripts/tune_semantic_thresholds.py
"""Tune semantic-router per-route thresholds against the real-customer baseline.

Dev/CI only — NOT imported at runtime. Reads the customer RVTools file
(if present), labels each VM with the override registry as ground truth, fits
the SemanticRouter thresholds on the unmatched remainder, and prints the
resulting per-route thresholds to paste into SemanticConfig / exemplars.

Usage:  rtk python scripts/tune_semantic_thresholds.py
"""

from __future__ import annotations

import os
from pathlib import Path

from store_predict.pipeline.classification import RuleRegistry, build_override_rules
from store_predict.pipeline.parsers.rvtools import parse_rvtools
from store_predict.pipeline.semantic_classifier import SemanticClassifier
from store_predict.services.semantic_config import SemanticConfig

# Override via the SEMANTIC_TUNE_FILE env var on machines without the default path.
CUSTOMER_FILE = Path(
    os.environ.get(
        "SEMANTIC_TUNE_FILE",
        "/Users/fjacquet/Library/CloudStorage/OneDrive-Home/20260430_1400_allvCenters.xlsx",
    )
)


def main() -> None:
    if not CUSTOMER_FILE.exists():
        print(f"Customer file not present: {CUSTOMER_FILE} — cannot tune.")
        return
    df = parse_rvtools(CUSTOMER_FILE)
    df = df[df["is_powered_on"]].reset_index(drop=True)
    registry = RuleRegistry(build_override_rules())

    x: list[str] = []
    y: list[str | None] = []
    for _, row in df.iterrows():
        name = str(row.get("vm_name") or "")
        os_name = str(row.get("os_name") or "")
        text = f"{name} {os_name}".strip()
        if not text:
            continue
        verdict = registry.classify(name, os_name)
        # rule_match -> ground-truth route label; otherwise None (should not force a route)
        x.append(text)
        y.append(f"{verdict.category}|{verdict.subcategory}" if verdict.confidence == "rule_match" else None)

    sem = SemanticClassifier(config=SemanticConfig())
    print("Before:", sem._router.get_thresholds())
    print("Accuracy before:", sem._router.evaluate(X=x, y=y))
    sem._router.fit(X=x, y=y, max_iter=500)
    print("After:", sem._router.get_thresholds())
    print("Accuracy after:", sem._router.evaluate(X=x, y=y))


if __name__ == "__main__":
    main()
