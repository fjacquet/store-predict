"""Tests for services/concerns_export.py -- CSV and PDF generators."""

from __future__ import annotations

import pandas as pd

from store_predict.pipeline.health_checks import HealthCheckResult, run_health_checks
from store_predict.services.concerns_export import generate_concerns_csv, generate_concerns_pdf

# ---------------------------------------------------------------------------
# Test data builders (mirrors test_health_checks.py _make_active_df pattern)
# ---------------------------------------------------------------------------


def _make_active_df(**overrides: object) -> pd.DataFrame:
    """Build a minimal canonical DataFrame with one active, non-template VM."""
    defaults: dict[str, list[object]] = {
        "vm_name": ["test-vm-01"],
        "os_name": ["Windows Server 2022"],
        "workload_category": ["Virtual Machines/VMware / Hyper-V / KVM - No Database, File nor Email"],
        "provisioned_mib": [102400.0],
        "in_use_mib": [51200.0],
        "num_cpus": [4],
        "memory_mib": [8192.0],
        "datacenter": ["DC1"],
        "cluster": ["Cluster-01"],
        "is_powered_on": [True],
        "is_template": [False],
        "hw_version": [19],
        "tools_status": ["toolsOk"],
        "peak_iops": [500.0],
        "avg_iops": [300.0],
        "source_format": ["rvtools"],
        "row_index": [0],
    }
    for key, val in overrides.items():
        defaults[key] = val  # type: ignore[assignment]
    return pd.DataFrame(defaults)


def _make_empty_result() -> HealthCheckResult:
    """Return a HealthCheckResult with no findings (has_data=False)."""
    return run_health_checks(None)


def _make_result_with_findings() -> HealthCheckResult:
    """Return a HealthCheckResult with at least one finding (tools not installed)."""
    df = _make_active_df(tools_status=["toolsNotInstalled"])
    return run_health_checks(df)


def _make_result_two_findings() -> HealthCheckResult:
    """Return a HealthCheckResult with exactly 2 findings (missing OS + zero provisioned)."""
    df = _make_active_df(os_name=[""], provisioned_mib=[0.0])
    return run_health_checks(df)


# ---------------------------------------------------------------------------
# CSV tests
# ---------------------------------------------------------------------------


class TestGenerateConcernsCsvHeader:
    def test_generate_concerns_csv_header_row(self) -> None:
        """CSV output must start with the expected header row."""
        result = _make_empty_result()
        csv_bytes = generate_concerns_csv(result)
        decoded = csv_bytes.decode("utf-8-sig")
        first_line = decoded.splitlines()[0]
        assert first_line == "severity,check_id,title,detail,remediation,affected_count,cluster"


class TestGenerateConcernsCsvRows:
    def test_generate_concerns_csv_one_row_per_finding(self) -> None:
        """CSV has header + one row per finding."""
        result = _make_result_two_findings()
        finding_count = len(result.findings)
        assert finding_count >= 2, f"Expected at least 2 findings, got {finding_count}"
        csv_bytes = generate_concerns_csv(result)
        decoded = csv_bytes.decode("utf-8-sig")
        lines = [line for line in decoded.splitlines() if line.strip()]
        # header + N data rows (one per finding)
        assert len(lines) == finding_count + 1

    def test_generate_concerns_csv_empty_findings(self) -> None:
        """Empty findings produce a header-only CSV without error."""
        result = _make_empty_result()
        csv_bytes = generate_concerns_csv(result)
        decoded = csv_bytes.decode("utf-8-sig")
        lines = [line for line in decoded.splitlines() if line.strip()]
        assert len(lines) == 1
        assert lines[0].startswith("severity")

    def test_generate_concerns_csv_utf8_bom(self) -> None:
        """CSV bytes must start with UTF-8 BOM for Excel compatibility."""
        result = _make_empty_result()
        csv_bytes = generate_concerns_csv(result)
        assert csv_bytes[:3] == b"\xef\xbb\xbf"

    def test_generate_concerns_csv_severity_column(self) -> None:
        """Severity column contains the string value (e.g. 'critical'), not the enum repr."""
        result = _make_result_with_findings()
        assert len(result.findings) >= 1
        csv_bytes = generate_concerns_csv(result)
        decoded = csv_bytes.decode("utf-8-sig")
        lines = decoded.splitlines()
        # First data row (line index 1) should have a valid severity string
        data_row = lines[1]
        severity_val = data_row.split(",")[0]
        assert severity_val in ("critical", "warning", "info")


# ---------------------------------------------------------------------------
# PDF tests
# ---------------------------------------------------------------------------


class TestGenerateConcernsPdf:
    def test_generate_concerns_pdf_returns_bytes(self) -> None:
        """PDF output must be bytes starting with %PDF magic."""
        result = _make_result_with_findings()
        pdf_bytes = generate_concerns_pdf(result)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_concerns_pdf_empty_findings(self) -> None:
        """Empty result generates a valid PDF without raising."""
        result = _make_empty_result()
        pdf_bytes = generate_concerns_pdf(result)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_concerns_pdf_with_project_name(self) -> None:
        """PDF with project name returns bytes (smoke test — no string search per CLAUDE.md gotcha)."""
        result = _make_result_with_findings()
        pdf_bytes = generate_concerns_pdf(result, project_name="Acme Corp Migration 2026")
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_concerns_pdf_locale_param_accepted(self) -> None:
        """generate_concerns_pdf accepts a locale parameter without raising."""
        result = _make_result_with_findings()
        pdf_fr = generate_concerns_pdf(result, locale="fr")
        pdf_en = generate_concerns_pdf(result, locale="en")
        assert isinstance(pdf_fr, bytes)
        assert isinstance(pdf_en, bytes)

    def test_generate_concerns_pdf_multiple_findings(self) -> None:
        """PDF with multiple findings (various severities) generates without error."""
        df = _make_active_df(
            os_name=[""],
            provisioned_mib=[0.0],
            tools_status=["toolsNotInstalled"],
        )
        result = run_health_checks(df)
        pdf_bytes = generate_concerns_pdf(result)
        assert pdf_bytes[:4] == b"%PDF"
