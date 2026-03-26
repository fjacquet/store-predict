"""Tests for make_sankey_image_flowable DPI, palette, and return-type guarantees."""

from __future__ import annotations

import inspect

from reportlab.platypus import Image, Spacer

from store_predict.pipeline.calculation import (
    CalculationSummary,
    VMCalculation,
    WorkloadGroupResult,
)
from store_predict.services.pdf_charts import make_sankey_image_flowable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_summary(
    categories: list[tuple[str, int, float, float]] | None = None,
) -> CalculationSummary:
    """Build a minimal but real CalculationSummary.

    Each tuple: (name, vm_count, provisioned_mib, drr)
    """
    if categories is None:
        categories = [
            ("Database/Microsoft SQL", 3, 30720.0, 5.0),
            ("Virtual Machines", 2, 10240.0, 5.0),
        ]

    vm_calcs: list[VMCalculation] = []
    groups: list[WorkloadGroupResult] = []

    for cat_name, count, prov_mib, drr in categories:
        in_use = prov_mib * 0.6
        req = prov_mib / max(drr, 0.1)
        for i in range(count):
            vm_calcs.append(
                VMCalculation(
                    vm_name=f"{cat_name}-VM{i + 1}",
                    workload_category=cat_name,
                    provisioned_mib=prov_mib / count,
                    in_use_mib=in_use / count,
                    drr=drr,
                    required_mib=req / count,
                )
            )
        groups.append(
            WorkloadGroupResult(
                category=cat_name,
                vm_count=count,
                total_provisioned_mib=prov_mib,
                total_in_use_mib=in_use,
                avg_drr=drr,
                total_required_mib=req,
            )
        )

    total_prov = sum(g.total_provisioned_mib for g in groups)
    total_in_use = sum(g.total_in_use_mib for g in groups)
    total_req = sum(g.total_required_mib for g in groups)
    weighted_drr = total_prov / total_req if total_req > 0 else 0.0

    return CalculationSummary(
        vm_calculations=vm_calcs,
        workload_groups=groups,
        total_vms=len(vm_calcs),
        total_provisioned_mib=total_prov,
        total_in_use_mib=total_in_use,
        total_required_mib=total_req,
        weighted_avg_drr=weighted_drr,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSankeyImageFlowable:
    def test_sankey_returns_image_flowable(self) -> None:
        """make_sankey_image_flowable returns a ReportLab Image, not a Spacer."""
        summary = _make_summary()
        result = make_sankey_image_flowable(summary)
        assert isinstance(result, Image), f"Expected Image, got {type(result)}"
        assert not isinstance(result, Spacer)

    def test_sankey_dpi_300(self) -> None:
        """Sankey PNG renders at 300 DPI — pixel width >= 2000 for 500pt default width.

        ReportLab Image exposes imageWidth / imageHeight (the native pixel dimensions
        of the PNG that was passed in).  At 300 DPI with the default 500pt width:
          500 / 72 * 300 = 2083 px
        """
        summary = _make_summary()
        flowable = make_sankey_image_flowable(summary)
        assert isinstance(flowable, Image)

        # imageWidth is set by ReportLab from the PNG pixel dimensions
        width_px = flowable.imageWidth  # type: ignore[attr-defined]
        assert width_px >= 2000, (
            f"PNG width {width_px}px is below 2000px — DPI is not 300 (expected >= 2000)"
        )

    def test_sankey_palette_matches_echart(self) -> None:
        """Palette 6th color must be #DEE2E6 (matching ECharts DELL_PALETTE)."""
        src = inspect.getsource(make_sankey_image_flowable)
        assert '"#DEE2E6"' in src, (
            "make_sankey_image_flowable palette must contain '#DEE2E6' (ECharts match)"
        )
        assert '"#5B8DB8"' not in src, (
            "make_sankey_image_flowable must NOT contain old mismatched color '#5B8DB8'"
        )
