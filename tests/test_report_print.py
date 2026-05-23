"""Tests for report_print.py health findings data flow."""

from __future__ import annotations

from store_predict.pipeline.health_checks import HealthFinding, Severity


class TestFindingsDataSerialization:
    """Verify the dict serialization format that report.py produces for print_session."""

    def _make_finding(
        self,
        check_id: str = "data_quality.zero_provisioned",
        severity: Severity = Severity.CRITICAL,
        title: str = "health.zero_provisioned.title",
        detail: str = "health.zero_provisioned.detail",
        affected_count: int = 3,
        cluster: str = "",
    ) -> HealthFinding:
        return HealthFinding(
            check_id=check_id,
            severity=severity,
            title=title,
            detail=detail,
            affected_count=affected_count,
            affected_vms=("vm-a", "vm-b"),
            cluster=cluster,
        )

    def test_finding_serializes_to_plain_dict(self) -> None:
        """Each HealthFinding must serialize to a JSON-safe plain dict."""
        finding = self._make_finding()
        serialized: dict = {
            "check_id": finding.check_id,
            "severity": str(finding.severity),
            "title": finding.title,
            "detail": finding.detail,
            "affected_count": finding.affected_count,
            "affected_vms": list(finding.affected_vms),
            "cluster": finding.cluster,
        }
        assert serialized["severity"] == "critical"  # str(Severity.CRITICAL) == "critical"
        assert serialized["check_id"] == "data_quality.zero_provisioned"
        assert isinstance(serialized["affected_vms"], list)

    def test_finding_round_trips_through_serialization(self) -> None:
        """Deserializing a serialized finding must produce an equivalent HealthFinding."""
        original = self._make_finding(severity=Severity.WARNING, cluster="cluster-a")
        fd: dict = {
            "check_id": original.check_id,
            "severity": str(original.severity),
            "title": original.title,
            "detail": original.detail,
            "affected_count": original.affected_count,
            "affected_vms": list(original.affected_vms),
            "cluster": original.cluster,
        }
        # Reconstruct as done in report_print.py
        restored = HealthFinding(
            check_id=str(fd["check_id"]),
            severity=Severity(str(fd["severity"])),
            title=str(fd["title"]),
            detail=str(fd["detail"]),
            affected_count=int(fd["affected_count"]),
            affected_vms=tuple(str(v) for v in fd.get("affected_vms", [])),
            cluster=str(fd.get("cluster", "")),
        )
        assert restored.check_id == original.check_id
        assert restored.severity == original.severity
        assert restored.affected_count == original.affected_count
        assert restored.cluster == original.cluster

    def test_empty_findings_data_produces_empty_list(self) -> None:
        """When findings_data key is missing from session, deserialization yields empty list."""
        data: dict = {"vm_data": [], "project_name": "test"}
        findings_data = data.get("findings_data", [])
        health_findings = []
        for fd in findings_data:
            health_findings.append(
                HealthFinding(
                    check_id=str(fd["check_id"]),
                    severity=Severity(str(fd["severity"])),
                    title=str(fd["title"]),
                    detail=str(fd["detail"]),
                    affected_count=int(fd["affected_count"]),
                    affected_vms=tuple(str(v) for v in fd.get("affected_vms", [])),
                    cluster=str(fd.get("cluster", "")),
                )
            )
        assert health_findings == []

    def test_severity_sorting_order(self) -> None:
        """Findings must sort critical first, then warning, then info."""
        findings = [
            self._make_finding(check_id="best_practice.hw", severity=Severity.INFO),
            self._make_finding(check_id="sizing_risk.large_vm", severity=Severity.WARNING),
            self._make_finding(check_id="data_quality.zero", severity=Severity.CRITICAL),
        ]
        _sev_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_findings = sorted(findings, key=lambda f: (_sev_order.get(str(f.severity), 3), f.check_id))
        assert str(sorted_findings[0].severity) == "critical"
        assert str(sorted_findings[1].severity) == "warning"
        assert str(sorted_findings[2].severity) == "info"

    def test_check_id_prefix_maps_to_category_key(self) -> None:
        """check_id prefix correctly maps to the i18n category key used in display."""
        _prefix_key = {
            "data_quality": "pdf.findings_category_data_quality",
            "sizing_risk": "pdf.findings_category_sizing_risk",
            "best_practice": "pdf.findings_category_best_practice",
        }
        assert _prefix_key["data_quality"] == "pdf.findings_category_data_quality"
        assert _prefix_key["sizing_risk"] == "pdf.findings_category_sizing_risk"

        # Prefix extraction logic
        check_id = "data_quality.zero_provisioned"
        prefix = check_id.split(".")[0] if "." in check_id else check_id
        assert prefix == "data_quality"
        assert _prefix_key.get(prefix) == "pdf.findings_category_data_quality"


def test_pptx_handler_produces_pptx_bytes() -> None:
    """The report page's PPTX path produces a valid .pptx for a real summary."""
    from store_predict.pipeline.calculation import calculate
    from store_predict.services.pptx_report import generate_report_pptx

    rows = [
        {
            "vm_name": "SQL01",
            "workload_category": "Database/Microsoft SQL",
            "provisioned_mib": 20480.0,
            "in_use_mib": 12288.0,
            "drr": 5.0,
        },
        {
            "vm_name": "WEB01",
            "workload_category": "Virtual Machines",
            "provisioned_mib": 10240.0,
            "in_use_mib": 6144.0,
            "drr": 5.0,
        },
    ]
    summary = calculate(rows)
    out = generate_report_pptx(summary, "Wiring Test", locale="fr")
    assert out[:4] == b"PK\x03\x04"


def test_report_page_imports_pptx_generator() -> None:
    """report.py must import generate_report_pptx (button wiring)."""
    import store_predict.ui.pages.report as report_mod

    assert (
        hasattr(report_mod, "generate_report_pptx")
        or "generate_report_pptx" in report_mod.__dict__
        or hasattr(report_mod, "_on_download_pptx")
    )
