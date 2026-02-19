"""Performance benchmark tests for classification and PDF generation.

Verifies NFR-4.1 (5000 VMs without timeout) and NFR-4.2 (PDF generation under 5 seconds).
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pandas as pd

from store_predict.pipeline.calculation import (
    CalculationSummary,
    WorkloadGroupResult,
)
from store_predict.pipeline.classification import (
    RuleRegistry,
    build_default_rules,
    classify_dataframe,
)
from store_predict.services.pdf_report import generate_report_pdf

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VM_NAME_PREFIXES = [
    "SQL-SRV-",
    "ORACLE-DB-",
    "SAP-APP-",
    "VDI-PC-",
    "EXCHANGE-",
    "WEB-SRV-",
    "FILE-SRV-",
    "DOCKER-",
    "VEEAM-",
    "ELASTIC-",
    "APP-SRV-",
    "DC-",
    "CITRIX-",
    "PGSQL-",
    "MONGO-",
]

_OS_VALUES = [
    "Microsoft Windows Server 2019",
    "Red Hat Enterprise Linux 8",
    "Ubuntu 22.04",
    "Microsoft Windows Server 2022",
    "SUSE Linux Enterprise Server 15",
]


def make_large_dataframe(n: int = 5000) -> pd.DataFrame:
    """Create a synthetic DataFrame with *n* VM rows for benchmarking."""
    vm_names = [f"{_VM_NAME_PREFIXES[i % len(_VM_NAME_PREFIXES)]}{i:04d}" for i in range(n)]
    os_names = [_OS_VALUES[i % len(_OS_VALUES)] for i in range(n)]
    provisioned = [50_000.0 + (i % 100) * 100 for i in range(n)]
    in_use = [p * 0.6 for p in provisioned]

    return pd.DataFrame(
        {
            "vm_name": vm_names,
            "os_name": os_names,
            "provisioned_mib": provisioned,
            "in_use_mib": in_use,
            "is_template": [False] * n,
        }
    )


def _make_workload_groups(count: int = 15) -> list[WorkloadGroupResult]:
    """Create *count* synthetic workload group results."""
    categories = [
        "Database/Microsoft SQL",
        "Database/Oracle",
        "Database/SAP HANA(S4)",
        "VDI/Full Clone",
        "VDI/Linked Clone",
        "Email/Exchange",
        "Virtual Machines",
        "File/General Purpose",
        "Containers/Kubernetes",
        "Web Servers",
        "Logging - Analytics",
        "VM Replication",
        "Boot from SAN",
        "Database/PostgreSQL",
        "File/Content Servers",
    ]
    groups = []
    for i in range(count):
        cat = categories[i % len(categories)]
        vm_count = 50 + i * 10
        provisioned = float(vm_count) * 50_000.0
        drr = 3.0 + (i % 5)
        required = provisioned / drr
        groups.append(
            WorkloadGroupResult(
                category=cat,
                vm_count=vm_count,
                total_provisioned_mib=provisioned,
                total_in_use_mib=provisioned * 0.6,
                avg_drr=drr,
                total_required_mib=required,
            )
        )
    return groups


# ---------------------------------------------------------------------------
# Benchmark tests
# ---------------------------------------------------------------------------


class TestClassificationPerformance:
    """NFR-4.1: Classification of 5000 VMs completes in under 10 seconds."""

    def test_classification_5000_vms_under_10s(self) -> None:
        df = make_large_dataframe(5000)
        registry = RuleRegistry(build_default_rules())

        start = time.perf_counter()
        result = classify_dataframe(df, registry)
        elapsed = time.perf_counter() - start

        assert len(result) == 5000, f"Expected 5000 rows, got {len(result)}"
        assert elapsed < 10.0, f"Classification took {elapsed:.2f}s, exceeds 10s limit"
        # Verify classification columns were added
        for col in ("workload_category", "workload_subcategory", "classification_rule"):
            assert col in result.columns, f"Missing column: {col}"


class TestPDFGenerationPerformance:
    """NFR-4.2: PDF generation for a large summary completes in under 5 seconds."""

    def test_pdf_generation_under_5s(self) -> None:
        groups = _make_workload_groups(15)
        total_vms = sum(g.vm_count for g in groups)
        total_provisioned = sum(g.total_provisioned_mib for g in groups)
        total_in_use = sum(g.total_in_use_mib for g in groups)
        total_required = sum(g.total_required_mib for g in groups)
        weighted_drr = total_provisioned / total_required if total_required > 0 else 0.0

        summary = CalculationSummary(
            vm_calculations=[],  # PDF only uses workload_groups for the table
            workload_groups=groups,
            total_vms=total_vms,
            total_provisioned_mib=total_provisioned,
            total_in_use_mib=total_in_use,
            total_required_mib=total_required,
            weighted_avg_drr=weighted_drr,
        )

        tmp_path: Path | None = None
        try:
            start = time.perf_counter()
            pdf_bytes = generate_report_pdf(summary, "Large Benchmark Project")
            elapsed = time.perf_counter() - start

            # Write to temp file to verify it's valid
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(pdf_bytes)
                tmp_path = Path(f.name)

            assert tmp_path.exists(), "PDF file was not created"
            assert tmp_path.stat().st_size > 0, "PDF file is empty"
            assert elapsed < 5.0, f"PDF generation took {elapsed:.2f}s, exceeds 5s limit"
        finally:
            if tmp_path and tmp_path.exists():
                tmp_path.unlink()
