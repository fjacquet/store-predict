"""Concerns page — health check findings from session data."""

from __future__ import annotations

from nicegui import ui

from store_predict.i18n import t
from store_predict.pipeline.health_checks import HealthCheckResult, HealthFinding, Severity, run_health_checks
from store_predict.services.concerns_export import generate_concerns_csv, generate_concerns_pdf
from store_predict.ui.layout import layout
from store_predict.ui.state import load_filtered_session_data

# ---------------------------------------------------------------------------
# Severity styling helpers
# ---------------------------------------------------------------------------

_SEVERITY_CARD_STYLE: dict[Severity, str] = {
    Severity.CRITICAL: (
        "border-left:4px solid var(--q-negative);background:color-mix(in srgb,var(--q-negative) 8%,var(--sp-surface));"
    ),
    Severity.WARNING: (
        "border-left:4px solid var(--q-warning);background:color-mix(in srgb,var(--q-warning) 8%,var(--sp-surface));"
    ),
    Severity.INFO: (
        "border-left:4px solid var(--q-info);background:color-mix(in srgb,var(--q-info) 8%,var(--sp-surface));"
    ),
}

_SEVERITY_BADGE_COLOR: dict[Severity, str] = {
    Severity.CRITICAL: "negative",
    Severity.WARNING: "warning",
    Severity.INFO: "info",
}

_SEVERITY_TITLE_STYLE: dict[Severity, str] = {
    Severity.CRITICAL: "color:var(--q-negative);font-weight:600;",
    Severity.WARNING: "color:var(--q-warning);font-weight:600;",
    Severity.INFO: "color:var(--q-info);font-weight:600;",
}


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_summary_badges(result: HealthCheckResult) -> None:
    """Render critical/warning/info count badges in a horizontal row."""
    with ui.row().classes("gap-3 items-center flex-wrap"):
        if result.critical_count > 0:
            ui.badge(
                t("concerns.summary_critical", count=result.critical_count),
                color="negative",
            ).classes("text-sm font-bold px-3 py-1 rounded-full")
        if result.warning_count > 0:
            ui.badge(
                t("concerns.summary_warning", count=result.warning_count),
                color="warning",
            ).classes("text-sm font-bold px-3 py-1 rounded-full")
        if result.info_count > 0:
            ui.badge(
                t("concerns.summary_info", count=result.info_count),
                color="info",
            ).classes("text-sm font-bold px-3 py-1 rounded-full")
        ui.label(t("concerns.affected_count", count=result.total_vms_checked)).classes("text-sm").style(
            "color:var(--sp-muted)"
        )


def _render_finding_card(finding: HealthFinding) -> None:
    """Render a single finding as a left-bordered card with severity color."""
    card_style = _SEVERITY_CARD_STYLE.get(
        finding.severity,
        "border-left:4px solid var(--sp-line);background:var(--sp-surface-2);",
    )
    badge_color = _SEVERITY_BADGE_COLOR.get(finding.severity, "grey-7")
    title_style = _SEVERITY_TITLE_STYLE.get(finding.severity, "color:var(--sp-muted);font-weight:600;")

    with ui.card().classes("w-full p-4 gap-2").style(card_style):
        with ui.row().classes("items-center gap-2 flex-wrap"):
            ui.badge(finding.severity.upper(), color=badge_color).classes("text-xs font-bold px-2 py-0.5 rounded")
            ui.label(t(finding.title)).classes("font-semibold").style(title_style)
            if finding.cluster:
                ui.label(finding.cluster).classes("text-xs sp-mono px-2 py-0.5 rounded").style(
                    "background:var(--sp-surface-2);border:1px solid var(--sp-line);color:var(--sp-muted)"
                )
        ui.label(t(finding.detail, count=finding.affected_count)).classes("text-sm").style("color:var(--sp-muted)")
        if finding.remediation:
            ui.label(finding.remediation).classes("text-sm italic mt-1").style("color:var(--sp-muted)")
        if finding.affected_vms:
            names_str = ", ".join(finding.affected_vms)
            ui.label(t("concerns.affected_vms", names=names_str)).classes("text-xs sp-mono").style(
                "color:var(--sp-muted)"
            )


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
        ui.label(section_title).classes("text-lg font-bold mt-2").style("color:var(--sp-muted)")
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
# Export helpers
# ---------------------------------------------------------------------------


def _get_locale() -> str:
    """Return the current locale from tab storage, defaulting to 'fr'."""
    from nicegui import app

    return str(app.storage.tab.get("locale", "fr"))


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

    df = load_filtered_session_data()

    if df is None or df.empty:
        with (
            layout("StorePredict - " + t("concerns.title")),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("health_and_safety", size="3rem").style("color:var(--sp-muted)")
            ui.label(t("concerns.no_data")).classes("text-xl text-center").style("color:var(--sp-muted)")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).props("color=primary")
        return

    result = run_health_checks(df)

    with layout("StorePredict - " + t("concerns.title")), ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        ui.label(t("concerns.title")).classes("text-2xl font-bold sp-display")
        _render_summary_badges(result)
        with ui.row().classes("gap-2 items-center"):
            ui.button(
                t("concerns.export_pdf"),
                icon="picture_as_pdf",
                on_click=lambda: ui.download(
                    generate_concerns_pdf(result, locale=_get_locale()),
                    t("concerns.export_pdf_filename"),
                ),
            ).classes("text-sm").props("color=primary")
            ui.button(
                t("concerns.export_csv"),
                icon="download",
                on_click=lambda: ui.download(
                    generate_concerns_csv(result),
                    t("concerns.export_csv_filename"),
                ),
            ).classes("text-sm").props("color=positive")
        ui.separator()
        if not result.findings:
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle", size="1.5rem").props("color=positive")
                ui.label(t("concerns.no_findings")).classes("font-medium").style("color:var(--q-positive)")
        else:
            _render_findings_by_severity(result.findings)
