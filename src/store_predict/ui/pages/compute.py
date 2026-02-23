"""Compute Sizing page — ESXi host count recommendations from session data.

ANTI-PATTERNS — never do these here:
- Never call classify_dataframe() or any ingestion pipeline function
- Never store ComputeSizingResult in app.storage.tab (only store config inputs)
- Always use load_session_data() for the DataFrame
"""

from __future__ import annotations

from typing import TypedDict

from nicegui import app, ui

from store_predict.i18n import t
from store_predict.pipeline.compute_sizing import (
    DELL_POWEREDGE_PRESETS,
    ClusterSizingRow,
    ComputeSizingResult,
    HostConfig,
    compute_cluster_breakdown,
    compute_sizing,
)
from store_predict.ui.layout import layout
from store_predict.ui.state import load_session_data

# ---------------------------------------------------------------------------
# Session config type
# ---------------------------------------------------------------------------


class _ComputeConfig(TypedDict):
    preset_name: str
    overcommit_ratio: float
    vmsc_enabled: bool
    ap_enabled: bool
    custom_cores_per_socket: int
    custom_sockets: int
    custom_ram_gib: int


# ---------------------------------------------------------------------------
# Session config helpers
# ---------------------------------------------------------------------------

_PRESET_NAMES = [p.name for p in DELL_POWEREDGE_PRESETS]
_PRESET_BY_NAME = {p.name: p for p in DELL_POWEREDGE_PRESETS}
_DEFAULT_PRESET = _PRESET_NAMES[0]  # "R760"


def _load_compute_config() -> _ComputeConfig:
    """Load compute sizing config from tab-scoped session storage."""
    preset_name = str(app.storage.tab.get("compute_preset", _DEFAULT_PRESET))
    preset = _PRESET_BY_NAME.get(preset_name) or DELL_POWEREDGE_PRESETS[-1]
    return {
        "preset_name": preset_name,
        "overcommit_ratio": float(app.storage.tab.get("compute_overcommit", 4.0)),
        "vmsc_enabled": bool(app.storage.tab.get("compute_vmsc", False)),
        "ap_enabled": bool(app.storage.tab.get("compute_ap", False)),
        "custom_cores_per_socket": int(app.storage.tab.get("compute_custom_cps", preset.cores_per_socket)),
        "custom_sockets": int(app.storage.tab.get("compute_custom_sockets", preset.sockets)),
        "custom_ram_gib": int(app.storage.tab.get("compute_custom_ram", preset.ram_gib)),
    }


def _resolve_host_config(cfg: _ComputeConfig) -> HostConfig:
    """Return HostConfig from session config. Always uses field values."""
    return HostConfig(
        name=str(cfg["preset_name"]),
        cores_per_socket=cfg["custom_cores_per_socket"],
        sockets=cfg["custom_sockets"],
        ram_gib=cfg["custom_ram_gib"],
    )


# ---------------------------------------------------------------------------
# Aggregate display helper
# ---------------------------------------------------------------------------


def _render_aggregate_cards(result: ComputeSizingResult) -> None:
    """Render vCPU, RAM, and excluded VM count cards in a 3-column row."""
    with ui.row().classes("w-full gap-4 flex-wrap"):
        with ui.card().classes("flex-1 min-w-40 p-4 text-center"):
            ui.label(t("compute.active_vcpus")).classes("text-sm text-gray-500")
            ui.label(str(result.total_active_vcpus)).classes("text-3xl font-bold text-blue-700")
        with ui.card().classes("flex-1 min-w-40 p-4 text-center"):
            ui.label(t("compute.active_ram")).classes("text-sm text-gray-500")
            ui.label(f"{result.total_active_ram_gib:.1f}").classes("text-3xl font-bold text-blue-700")
        if result.excluded_vm_count > 0:
            with ui.card().classes("flex-1 min-w-40 p-4 text-center bg-gray-50"):
                ui.label(t("compute.excluded_vms", count=result.excluded_vm_count)).classes("text-sm text-gray-500")


# ---------------------------------------------------------------------------
# Per-cluster breakdown table
# ---------------------------------------------------------------------------


def _render_cluster_breakdown_table(
    cluster_rows: list[ClusterSizingRow],
) -> None:
    """Render per-cluster breakdown as a ui.table with grand total row.

    Suppressed if fewer than 2 distinct clusters (single-cluster or
    no-cluster environments — grand total duplicates global figures).
    Also suppressed if all VMs are in the __no_cluster__ sentinel group.
    Shows an informational note explaining the N+1 buffer difference.
    """
    # Filter out the no-cluster sentinel to determine real cluster count
    real_clusters = [r for r in cluster_rows if r.cluster_name != "__no_cluster__"]

    if len(real_clusters) < 2:
        # Single cluster or LiveOptics (no cluster data): show note instead
        with ui.card().classes("w-full p-4 bg-gray-50 border-l-4 border-gray-300"):
            ui.label(t("compute.no_cluster_data_note")).classes("text-sm text-gray-500")
        return

    ui.separator()
    ui.label(t("compute.cluster_breakdown_heading")).classes("text-lg font-bold text-gray-700")

    columns = [
        {"name": "cluster", "label": t("compute.cluster_col"), "field": "cluster", "align": "left"},
        {"name": "vm_count", "label": t("compute.cluster_vm_count_col"), "field": "vm_count", "align": "right"},
        {"name": "vcpus", "label": t("compute.cluster_vcpu_col"), "field": "vcpus", "align": "right"},
        {"name": "ram_gib", "label": t("compute.cluster_ram_col"), "field": "ram_gib", "align": "right"},
        {"name": "hosts", "label": t("compute.cluster_hosts_col"), "field": "hosts", "align": "right"},
    ]

    # Build display rows — replace __no_cluster__ sentinel with i18n label
    rows = [
        {
            "cluster": t("compute.no_cluster_label") if r.cluster_name == "__no_cluster__" else r.cluster_name,
            "vm_count": str(r.vm_count),
            "vcpus": str(r.total_vcpus),
            "ram_gib": f"{r.total_ram_gib:.1f}",
            "hosts": str(r.hosts_needed),
        }
        for r in cluster_rows
    ]

    # Grand total row (CLUS-03)
    rows.append({
        "cluster": t("compute.cluster_total"),
        "vm_count": str(sum(r.vm_count for r in cluster_rows)),
        "vcpus": str(sum(r.total_vcpus for r in cluster_rows)),
        "ram_gib": f"{sum(r.total_ram_gib for r in cluster_rows):.1f}",
        "hosts": str(sum(r.hosts_needed for r in cluster_rows)),
    })

    ui.table(columns=columns, rows=rows).classes("w-full")
    ui.label(t("compute.cluster_breakdown_note")).classes("text-xs text-gray-400 mt-1")


# ---------------------------------------------------------------------------
# Results panel (refreshable)
# ---------------------------------------------------------------------------


@ui.refreshable
def _results_panel(df, cfg: _ComputeConfig) -> None:  # type: ignore[no-untyped-def]
    """Render host count results. Decorated with @ui.refreshable for reactive updates."""
    host_config = _resolve_host_config(cfg)
    result = compute_sizing(
        df,
        host_config,
        overcommit_ratio=cfg["overcommit_ratio"],
        vmsc_enabled=cfg["vmsc_enabled"],
    )

    if not result.has_data:
        with ui.card().classes("w-full p-4 bg-yellow-50 border-l-4 border-yellow-400"):
            ui.label(t("compute.no_data")).classes("text-yellow-800")
        return

    _render_aggregate_cards(result)

    ui.separator()
    ui.label(t("compute.results_heading")).classes("text-lg font-bold text-gray-700")

    # N+1 HA card
    constraint_label = (
        t("compute.constraint_vcpu") if result.hosts_by_vcpu >= result.hosts_by_ram else t("compute.constraint_ram")
    )
    with ui.card().classes("w-full p-4 gap-2"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("dns", size="1.5rem").classes("text-blue-600")
            ui.label(t("compute.hosts_n1")).classes("font-semibold text-blue-800")
            ui.label(str(result.hosts_n1)).classes("text-3xl font-bold text-blue-700")
        ui.label(t("compute.hosts_n1_detail")).classes("text-sm text-gray-500")
        ui.label(f"{t('compute.binding_constraint')}: {constraint_label}").classes("text-xs text-gray-400")
        with ui.row().classes("gap-4 mt-1"):
            ui.label(f"{t('compute.breakdown_vcpu')}: {result.hosts_by_vcpu}").classes("text-xs text-gray-400")
            ui.label("·").classes("text-xs text-gray-300")
            ui.label(f"{t('compute.breakdown_ram')}: {result.hosts_by_ram}").classes("text-xs text-gray-400")

    # vMSC section (show if toggle active)
    if cfg["vmsc_enabled"]:
        with ui.card().classes("w-full p-4 gap-2"):
            ui.label(t("compute.vmsc_site_heading")).classes("font-semibold text-purple-800")
            if not result.vmsc_available:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("warning", size="1.2rem").classes("text-amber-500")
                    ui.label(t("compute.vmsc_no_dc_data")).classes("text-sm text-amber-700")
            else:
                for site in result.vmsc_sites:
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("location_on", size="1rem").classes("text-purple-500")
                        ui.label(f"{site}: {result.vmsc_hosts_per_site} hosts").classes("text-sm")

    # Active/Passive section (show if toggle active)
    if cfg["ap_enabled"]:
        with ui.card().classes("w-full p-4 gap-2"):
            ui.label(t("compute.ap_toggle")).classes("font-semibold text-green-800")
            with ui.row().classes("gap-6 flex-wrap"):
                with ui.column().classes("gap-1"):
                    ui.label(t("compute.ap_primary")).classes("text-sm text-gray-500")
                    ui.label(str(result.ap_primary_hosts)).classes("text-2xl font-bold text-green-700")
                with ui.column().classes("gap-1"):
                    ui.label(t("compute.ap_secondary")).classes("text-sm text-gray-500")
                    ui.label(str(result.ap_secondary_hosts)).classes("text-2xl font-bold text-gray-600")
                    ui.label(t("compute.ap_secondary_detail")).classes("text-xs text-gray-400")

    # Per-cluster breakdown (CLUS-02, CLUS-03)
    cluster_rows = compute_cluster_breakdown(
        df,
        host_config,
        overcommit_ratio=cfg["overcommit_ratio"],
    )
    if cluster_rows:
        _render_cluster_breakdown_table(cluster_rows)


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------


def _render_settings_panel(cfg: _ComputeConfig, refresh_fn) -> None:  # type: ignore[no-untyped-def]
    """Render preset selector, overcommit input, and mode toggles."""
    with ui.card().classes("w-full p-4 gap-4"):
        # Preset selector
        preset_select = (
            ui.select(
                _PRESET_NAMES,
                value=cfg["preset_name"],
                label=t("compute.host_preset"),
            )
            .classes("w-full")
            .tooltip(t("tooltip.compute_preset"))
        )

        # Host spec inputs — always visible; auto-populated when a named preset is chosen
        ui.separator()
        ui.label(t("compute.host_specs_heading")).classes("text-sm font-semibold text-gray-600")
        with ui.row().classes("gap-4 flex-wrap"):
            cps_input = ui.number(
                label=t("compute.cores_per_socket"),
                value=cfg["custom_cores_per_socket"],
                min=1,
                max=256,
                step=1,
            ).classes("w-32")
            sockets_input = ui.number(
                label=t("compute.sockets"),
                value=cfg["custom_sockets"],
                min=1,
                max=8,
                step=1,
            ).classes("w-24")
            ram_input = ui.number(
                label=t("compute.ram_gib"),
                value=cfg["custom_ram_gib"],
                min=16,
                max=24576,
                step=64,
            ).classes("w-32")

        # Overcommit ratio
        overcommit_input = (
            ui.number(
                label=t("compute.overcommit_ratio"),
                value=cfg["overcommit_ratio"],
                min=0.5,
                max=20.0,
                step=0.5,
            )
            .classes("w-48")
            .tooltip(t("tooltip.compute_overcommit"))
        )
        ui.label(t("compute.overcommit_hint")).classes("text-xs text-gray-400")

        ui.separator()

        # vMSC toggle
        vmsc_switch = ui.switch(
            t("compute.vmsc_toggle"),
            value=cfg["vmsc_enabled"],
        ).tooltip(t("tooltip.compute_vmsc"))

        # Active/Passive toggle
        ap_switch = ui.switch(
            t("compute.ap_toggle"),
            value=cfg["ap_enabled"],
        ).tooltip(t("tooltip.compute_ap"))

    # Wire on_change callbacks — save to session, then refresh results
    def _on_preset_change(e) -> None:  # type: ignore[no-untyped-def]
        preset_name = e.value
        app.storage.tab["compute_preset"] = preset_name
        preset = _PRESET_BY_NAME.get(preset_name)
        if preset and preset.name != "Custom":
            app.storage.tab["compute_custom_cps"] = preset.cores_per_socket
            app.storage.tab["compute_custom_sockets"] = preset.sockets
            app.storage.tab["compute_custom_ram"] = preset.ram_gib
            cps_input.set_value(preset.cores_per_socket)
            sockets_input.set_value(preset.sockets)
            ram_input.set_value(preset.ram_gib)
        refresh_fn()

    def _on_overcommit_change(e) -> None:  # type: ignore[no-untyped-def]
        if e.value is not None:
            app.storage.tab["compute_overcommit"] = float(e.value)
            refresh_fn()

    def _on_vmsc_change(e) -> None:  # type: ignore[no-untyped-def]
        app.storage.tab["compute_vmsc"] = bool(e.value)
        refresh_fn()

    def _on_ap_change(e) -> None:  # type: ignore[no-untyped-def]
        app.storage.tab["compute_ap"] = bool(e.value)
        refresh_fn()

    def _on_custom_cps_change(e) -> None:  # type: ignore[no-untyped-def]
        if e.value is not None:
            app.storage.tab["compute_custom_cps"] = int(e.value)
            refresh_fn()

    def _on_custom_sockets_change(e) -> None:  # type: ignore[no-untyped-def]
        if e.value is not None:
            app.storage.tab["compute_custom_sockets"] = int(e.value)
            refresh_fn()

    def _on_custom_ram_change(e) -> None:  # type: ignore[no-untyped-def]
        if e.value is not None:
            app.storage.tab["compute_custom_ram"] = int(e.value)
            refresh_fn()

    preset_select.on_value_change(_on_preset_change)
    overcommit_input.on_value_change(_on_overcommit_change)
    vmsc_switch.on_value_change(_on_vmsc_change)
    ap_switch.on_value_change(_on_ap_change)
    cps_input.on_value_change(_on_custom_cps_change)
    sockets_input.on_value_change(_on_custom_sockets_change)
    ram_input.on_value_change(_on_custom_ram_change)


# ---------------------------------------------------------------------------
# Page entry point
# ---------------------------------------------------------------------------


@ui.page("/compute")
async def compute_page() -> None:
    """Compute Sizing page.

    Loads session data and renders reactive host count recommendations.
    Never re-runs ingestion — always uses load_session_data().
    ComputeSizingResult is computed on-demand from session config; never cached.
    """
    await ui.context.client.connected()
    df = load_session_data()

    if df is None or df.empty:
        with (
            layout("StorePredict - " + t("compute.title")),
            ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
            ui.card().classes("p-8 gap-4 items-center text-center"),
        ):
            ui.icon("memory", size="3rem").classes("text-gray-400")
            ui.label(t("compute.no_data")).classes("text-xl text-gray-500 text-center")
            ui.button(
                t("report.go_to_upload"),
                on_click=lambda: ui.navigate.to("/upload"),
                icon="arrow_forward",
            ).classes("bg-blue-700 text-white")
        return

    cfg = _load_compute_config()

    with layout("StorePredict - " + t("compute.title")), ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        ui.label(t("compute.title")).classes("text-2xl font-bold text-blue-900")
        ui.separator()

        with ui.row().classes("w-full gap-6 flex-wrap items-start"):
            with ui.column().classes("flex-1 min-w-72 gap-4"):
                _render_settings_panel(
                    cfg,
                    lambda: _results_panel.refresh(load_session_data(), _load_compute_config()),
                )

            with ui.column().classes("flex-2 min-w-72 gap-4"):
                _results_panel(df, cfg)
