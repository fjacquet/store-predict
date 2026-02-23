"""Concerns page — health check findings from session data."""

from __future__ import annotations

from nicegui import ui

from store_predict.i18n import t
from store_predict.pipeline.health_checks import HealthCheckResult, HealthFinding, Severity, run_health_checks
from store_predict.ui.layout import layout
from store_predict.ui.state import load_session_data

# ---------------------------------------------------------------------------
# Severity styling helpers
# ---------------------------------------------------------------------------

_SEVERITY_CARD_CLASSES: dict[Severity, str] = {
    Severity.CRITICAL: "border-l-4 border-red-500 bg-red-50 p-4 gap-2",
    Severity.WARNING: "border-l-4 border-yellow-500 bg-yellow-50 p-4 gap-2",
    Severity.INFO: "border-l-4 border-blue-500 bg-blue-50 p-4 gap-2",
}

_SEVERITY_BADGE_CLASSES: dict[Severity, str] = {
    Severity.CRITICAL: "bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded",
    Severity.WARNING: "bg-yellow-500 text-white text-xs font-bold px-2 py-0.5 rounded",
    Severity.INFO: "bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded",
}

_SEVERITY_TITLE_CLASSES: dict[Severity, str] = {
    Severity.CRITICAL: "font-semibold text-red-800",
    Severity.WARNING: "font-semibold text-yellow-800",
    Severity.INFO: "font-semibold text-blue-800",
}


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_summary_badges(result: HealthCheckResult) -> None:
    """Render critical/warning/info count badges in a horizontal row."""
    with ui.row().classes("gap-3 items-center flex-wrap"):
        if result.critical_count > 0:
            ui.label(t("concerns.summary_critical", count=result.critical_count)).classes(
                "bg-red-600 text-white text-sm font-bold px-3 py-1 rounded-full"
            )
        if result.warning_count > 0:
            ui.label(t("concerns.summary_warning", count=result.warning_count)).classes(
                "bg-yellow-500 text-white text-sm font-bold px-3 py-1 rounded-full"
            )
        if result.info_count > 0:
            ui.label(t("concerns.summary_info", count=result.info_count)).classes(
                "bg-blue-500 text-white text-sm font-bold px-3 py-1 rounded-full"
            )
        ui.label(t("concerns.affected_count", count=result.total_vms_checked)).classes("text-sm text-gray-500")


def _render_finding_card(finding: HealthFinding) -> None:
    """Render a single finding as a left-bordered card with severity color."""
    card_classes = _SEVERITY_CARD_CLASSES.get(finding.severity, "border-l-4 border-gray-400 bg-gray-50 p-4 gap-2")
    badge_classes = _SEVERITY_BADGE_CLASSES.get(finding.severity, "bg-gray-500 text-white text-xs px-2 py-0.5 rounded")
    title_classes = _SEVERITY_TITLE_CLASSES.get(finding.severity, "font-semibold text-gray-800")

    with ui.card().classes(f"w-full {card_classes}"):
        with ui.row().classes("items-center gap-2 flex-wrap"):
            ui.label(finding.severity.upper()).classes(badge_classes)
            ui.label(t(finding.title)).classes(title_classes)
            if finding.cluster:
                ui.label(finding.cluster).classes("text-xs font-mono bg-gray-100 text-gray-700 px-2 py-0.5 rounded")
        ui.label(t(finding.detail, count=finding.affected_count)).classes("text-sm text-gray-700")
        if finding.affected_vms:
            names_str = ", ".join(finding.affected_vms)
            ui.label(t("concerns.affected_vms", names=names_str)).classes("text-xs text-gray-500 font-mono")


def _render_findings_section(
    section_title: str,
    findings: list[HealthFinding],
) -> None:
    """Render a labelled section containing a list of finding cards.

    Skips rendering if there are no findings for this section.
    """
    if not findings:
        return
    with ui.column().classes("w-full gap-2"):
        ui.label(section_title).classes("text-lg font-bold text-gray-700 mt-2")
        for finding in findings:
            _render_finding_card(finding)


def _render_findings_by_severity(findings: tuple[HealthFinding, ...]) -> None:
    """Group and render findings into three labelled sections."""
    data_quality = [f for f in findings if f.check_id.startswith("data_quality.")]
    sizing_risk = [f for f in findings if f.check_id.startswith("sizing_risk.")]
    best_practice = [f for f in findings if f.check_id.startswith("best_practice.")]

    _render_findings_section(t("concerns.section_data_quality"), data_quality)
    _render_findings_section(t("concerns.section_sizing_risk"), sizing_risk)
    _render_findings_section(t("concerns.section_best_practice"), best_practice)


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


@ui.page("/concerns")
async def concerns_page() -> None:
    """Health check concerns page.

    Loads session data, runs health checks, and renders grouped findings.
    HealthCheckResult is NOT cached in session — recomputed on every visit so
    that workload edits from the Review page are immediately reflected.
    """
    await ui.context.client.connected()

    df = load_session_data()

    if df is None or df.empty:
        with (
            layout("StorePredict - " + t("concerns.title")),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("health_and_safety", size="3rem").classes("text-gray-400")
            ui.label(t("concerns.no_data")).classes("text-xl text-gray-500 text-center")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).classes("bg-blue-700 text-white")
        return

    result = run_health_checks(df)

    with layout("StorePredict - " + t("concerns.title")), ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        ui.label(t("concerns.title")).classes("text-2xl font-bold text-blue-900")
        _render_summary_badges(result)
        ui.separator()
        if not result.findings:
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle", size="1.5rem").classes("text-green-600")
                ui.label(t("concerns.no_findings")).classes("text-green-600 font-medium")
        else:
            _render_findings_by_severity(result.findings)
