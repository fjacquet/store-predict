"""Scope selection page -- choose datacenter(s)/cluster(s) to analyze."""

from __future__ import annotations

from typing import Any

from nicegui import app, ui

from store_predict.i18n import t
from store_predict.ui.layout import layout
from store_predict.ui.state import (
    get_scope_selection,
    load_session_data,
    save_scope_selection,
)


def _unique_non_empty(values: list[Any]) -> list[str]:
    """Return sorted unique non-empty string values."""
    return sorted({str(v) for v in values if v and str(v).strip()})


@ui.page("/scope")
async def scope_page() -> None:
    """Scope selection -- let user pick datacenter(s)/cluster(s) before review."""
    await ui.context.client.connected()
    df = load_session_data()

    if df is None:
        with (
            layout("StorePredict - Scope"),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("upload_file", size="3rem").style("color:var(--sp-muted)")
            ui.label(t("review.no_data")).classes("text-xl").style("color:var(--sp-muted)")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).props("color=primary")
        return

    # Extract unique values
    all_dcs = _unique_non_empty(df["datacenter"].tolist()) if "datacenter" in df.columns else []
    all_clusters = _unique_non_empty(df["cluster"].tolist()) if "cluster" in df.columns else []

    # If no datacenter/cluster data at all, skip straight to review
    if not all_dcs and not all_clusters:
        save_scope_selection([], [])
        ui.navigate.to("/review")
        return

    # Load previously saved selections (if user navigated back)
    prev_dcs, prev_clusters = get_scope_selection()

    project_name: str = str(app.storage.tab.get("project_name", ""))

    with (
        layout("StorePredict - Scope"),
        ui.column().classes("w-full max-w-3xl mx-auto p-8 gap-6"),
    ):
        ui.label(t("scope.title")).classes("text-3xl font-bold sp-display")
        if project_name:
            ui.label(t("review.project_label", name=project_name)).classes("text-lg").style("color:var(--sp-muted)")

        ui.label(t("scope.description")).style("color:var(--sp-muted)")

        # Summary card
        total_vms = len(df)
        with ui.card().classes("w-full p-4").style("background:var(--sp-surface-2);border:1px solid var(--sp-line)"):
            ui.label(t("scope.total_vms", count=total_vms, dcs=len(all_dcs), clusters=len(all_clusters))).classes(
                "text-sm"
            )

        dc_select = None
        cluster_select = None

        # Datacenter selection
        if all_dcs:
            ui.label(t("scope.datacenter_label")).classes("text-lg font-semibold mt-2")
            dc_select = (
                ui.select(
                    all_dcs,
                    multiple=True,
                    value=prev_dcs if prev_dcs else all_dcs,
                    label=t("scope.datacenter_placeholder"),
                )
                .classes("w-full")
                .props("use-chips clearable")
            )

        # Cluster selection
        if all_clusters:
            ui.label(t("scope.cluster_label")).classes("text-lg font-semibold mt-2")
            cluster_select = (
                ui.select(
                    all_clusters,
                    multiple=True,
                    value=prev_clusters if prev_clusters else all_clusters,
                    label=t("scope.cluster_placeholder"),
                )
                .classes("w-full")
                .props("use-chips clearable")
            )

        # VM count preview (reactive)
        preview_container = ui.column().classes("w-full")

        def _update_preview() -> None:
            selected_dcs = dc_select.value if dc_select else []
            selected_cls = cluster_select.value if cluster_select else []
            # Filter locally for preview count
            filtered = df
            if selected_dcs and "datacenter" in df.columns:
                filtered = filtered[filtered["datacenter"].isin(selected_dcs)]
            if selected_cls and "cluster" in df.columns:
                filtered = filtered[filtered["cluster"].isin(selected_cls)]
            preview_container.clear()
            _card = (
                ui.card().classes("w-full p-3").style("background:var(--sp-surface-2);border:1px solid var(--sp-line)")
            )
            with preview_container, _card:
                ui.label(t("scope.preview_count", count=len(filtered), total=total_vms)).classes("text-sm font-medium")

        _update_preview()
        if dc_select:
            dc_select.on_value_change(lambda _: _update_preview())
        if cluster_select:
            cluster_select.on_value_change(lambda _: _update_preview())

        # Action buttons
        with ui.row().classes("w-full justify-between mt-4"):
            ui.button(
                t("scope.select_all"),
                on_click=lambda: _select_all(dc_select, all_dcs, cluster_select, all_clusters),
                icon="select_all",
            ).props("flat color=grey-7")

            ui.button(
                t("scope.continue"),
                on_click=lambda: _on_continue(dc_select, all_dcs, cluster_select, all_clusters),
                icon="arrow_forward",
            ).props("color=primary")


def _select_all(
    dc_select: ui.select | None,
    all_dcs: list[str],
    cluster_select: ui.select | None,
    all_clusters: list[str],
) -> None:
    """Reset selections to include all values."""
    if dc_select:
        dc_select.set_value(all_dcs)
    if cluster_select:
        cluster_select.set_value(all_clusters)


def _on_continue(
    dc_select: ui.select | None,
    all_dcs: list[str],
    cluster_select: ui.select | None,
    all_clusters: list[str],
) -> None:
    """Save scope selection and navigate to review."""
    selected_dcs: list[str] = list(dc_select.value or []) if dc_select else []
    selected_cls: list[str] = list(cluster_select.value or []) if cluster_select else []

    # If all are selected, store empty list (= no filter)
    if set(selected_dcs) == set(all_dcs):
        selected_dcs = []
    if set(selected_cls) == set(all_clusters):
        selected_cls = []

    save_scope_selection(selected_dcs, selected_cls)
    ui.navigate.to("/review")
