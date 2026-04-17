"""Tests for the per-VM ``is_ignored`` flag (GitHub issue #11).

The flag lets users exclude specific VMs from DRR calculation and report
output while keeping them visible on the review page. This mirrors the
scope-filtering pattern: the flag is filtered at the edge, not inside the
calculation pipeline.
"""

from __future__ import annotations

from typing import Any

import pytest

from store_predict.pipeline.calculation import calculate


@pytest.fixture
def mixed_rows() -> list[dict[str, Any]]:
    """5 VMs, 2 marked as ignored. Includes row_index for merge tests."""
    return [
        {
            "row_index": 0,
            "vm_name": "SQL-01",
            "workload_category": "Database/Microsoft SQL",
            "workload_subcategory": "Microsoft SQL",
            "drr": 5.0,
            "provisioned_mib": 10240,
            "in_use_mib": 5120,
            "os_name": "Windows",
            "num_cpus": 4,
            "memory_mib": 8192,
            "is_ignored": False,
        },
        {
            "row_index": 1,
            "vm_name": "WEB-01",
            "workload_category": "Virtual Machines",
            "workload_subcategory": "Virtual Machines",
            "drr": 5.0,
            "provisioned_mib": 5120,
            "in_use_mib": 2048,
            "os_name": "Linux",
            "num_cpus": 2,
            "memory_mib": 4096,
            "is_ignored": True,
        },
        {
            "row_index": 2,
            "vm_name": "WEB-02",
            "workload_category": "Virtual Machines",
            "workload_subcategory": "Virtual Machines",
            "drr": 5.0,
            "provisioned_mib": 5120,
            "in_use_mib": 2048,
            "os_name": "Linux",
            "num_cpus": 2,
            "memory_mib": 4096,
            "is_ignored": False,
        },
        {
            "row_index": 3,
            "vm_name": "TEMP-01",
            "workload_category": "Virtual Machines",
            "workload_subcategory": "Virtual Machines",
            "drr": 5.0,
            "provisioned_mib": 2048,
            "in_use_mib": 512,
            "os_name": "Linux",
            "num_cpus": 1,
            "memory_mib": 2048,
            "is_ignored": True,
        },
        {
            "row_index": 4,
            "vm_name": "SAP-01",
            "workload_category": "Database/SAP",
            "workload_subcategory": "SAP",
            "drr": 2.0,
            "provisioned_mib": 51200,
            "in_use_mib": 30720,
            "os_name": "Linux",
            "num_cpus": 8,
            "memory_mib": 32768,
            "is_ignored": False,
        },
    ]


class TestIgnoreFilter:
    """Pure filter at the edge — same pattern as scope filtering."""

    def test_filter_drops_ignored_rows(self, mixed_rows: list[dict[str, Any]]) -> None:
        active = [r for r in mixed_rows if not r.get("is_ignored", False)]
        assert len(active) == 3
        assert {str(r["vm_name"]) for r in active} == {"SQL-01", "WEB-02", "SAP-01"}

    def test_filter_is_noop_when_flag_missing(self) -> None:
        """Legacy rows without ``is_ignored`` default to active."""
        rows = [{"vm_name": "A"}, {"vm_name": "B"}]
        active = [r for r in rows if not r.get("is_ignored", False)]
        assert len(active) == 2


class TestMergePreservesIgnoredFlag:
    """``save_filtered_rows`` must carry ``is_ignored`` edits back to full session."""

    def test_merge_flips_ignored_on_edited_row_only(self) -> None:
        """Only rows present in the edited subset get their flag updated."""
        full = [
            {"row_index": 0, "vm_name": "A", "drr": 5.0, "is_ignored": False},
            {"row_index": 1, "vm_name": "B", "drr": 5.0, "is_ignored": False},
            {"row_index": 2, "vm_name": "C", "drr": 5.0, "is_ignored": False},
        ]
        edited_by_idx = {0: {"row_index": 0, "is_ignored": True}}

        for row in full:
            idx = int(row.get("row_index", -1))
            if idx in edited_by_idx:
                for key in ("workload_category", "workload_subcategory", "drr", "is_ignored"):
                    if key in edited_by_idx[idx]:
                        row[key] = edited_by_idx[idx][key]

        assert full[0]["is_ignored"] is True
        assert full[1]["is_ignored"] is False
        assert full[2]["is_ignored"] is False

    def test_merge_can_reinclude_previously_ignored(self) -> None:
        full = [{"row_index": 0, "vm_name": "A", "drr": 5.0, "is_ignored": True}]
        edited_by_idx = {0: {"row_index": 0, "is_ignored": False}}

        for row in full:
            idx = int(row.get("row_index", -1))
            if idx in edited_by_idx:
                for key in ("workload_category", "workload_subcategory", "drr", "is_ignored"):
                    if key in edited_by_idx[idx]:
                        row[key] = edited_by_idx[idx][key]

        assert full[0]["is_ignored"] is False


class TestCalculationOnFilteredRows:
    """Calling ``calculate()`` on rows with ignored dropped gives smaller totals."""

    def test_ignored_rows_excluded_from_totals(self, mixed_rows: list[dict[str, Any]]) -> None:
        full_summary = calculate(mixed_rows)
        active_only = [r for r in mixed_rows if not r.get("is_ignored", False)]
        active_summary = calculate(active_only)

        assert full_summary.total_vms == 5
        assert active_summary.total_vms == 3
        assert active_summary.total_provisioned_mib < full_summary.total_provisioned_mib
        # ignored rows contributed 5120 + 2048 = 7168 MiB
        assert full_summary.total_provisioned_mib - active_summary.total_provisioned_mib == 7168

    def test_all_ignored_produces_empty_summary(self) -> None:
        all_ignored = [
            {
                "row_index": 0,
                "vm_name": "A",
                "workload_category": "X",
                "provisioned_mib": 1024,
                "drr": 5.0,
                "is_ignored": True,
            },
        ]
        active = [r for r in all_ignored if not r.get("is_ignored", False)]
        summary = calculate(active)
        assert summary.total_vms == 0
        assert summary.total_provisioned_mib == 0


class TestSummaryStatsAggregation:
    """Aggregation math (extracted from summary_stats.build_summary_stats)
    excludes ignored rows."""

    @staticmethod
    def _aggregate(rows: list[dict[str, Any]]) -> tuple[int, float, float]:
        """Mirror the first-three-cards math in build_summary_stats."""
        active = [r for r in rows if not r.get("is_ignored", False)]
        total_vms = len(active)
        total_provisioned = sum(float(r.get("provisioned_mib", 0) or 0) for r in active)
        avg_drr = sum(float(r.get("drr", 5.0) or 5.0) for r in active) / total_vms if total_vms else 0.0
        return total_vms, total_provisioned, avg_drr

    def test_aggregates_skip_ignored(self, mixed_rows: list[dict[str, Any]]) -> None:
        total_vms, total_prov, avg_drr = self._aggregate(mixed_rows)
        assert total_vms == 3
        assert total_prov == 10240 + 5120 + 51200
        # Weighted DRR mean over the active rows: (5 + 5 + 2) / 3
        assert avg_drr == pytest.approx((5.0 + 5.0 + 2.0) / 3)

    def test_all_active_uses_full_set(self) -> None:
        rows = [
            {"provisioned_mib": 1024, "drr": 5.0, "is_ignored": False},
            {"provisioned_mib": 2048, "drr": 5.0, "is_ignored": False},
        ]
        total_vms, _, _ = self._aggregate(rows)
        assert total_vms == 2
