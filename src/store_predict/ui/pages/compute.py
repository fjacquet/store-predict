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
    ComputeSizingResult,
    HostConfig,
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
_DEFAULT_PRESET = _PRESET_NAMES[0]  # "R760 (2x28c / 512 GiB)"


def _load_compute_config() -> _ComputeConfig:
    """Load compute sizing config from tab-scoped session storage."""
    return {
        "preset_name": app.storage.tab.get("compute_preset", _DEFAULT_PRESET),
        "overcommit_ratio": float(app.storage.tab.get("compute_overcommit", 4.0)),
        "vmsc_enabled": bool(app.storage.tab.get("compute_vmsc", False)),
        "ap_enabled": bool(app.storage.tab.get("compute_ap", False)),
        "custom_cores_per_socket": int(app.storage.tab.get("compute_custom_cps", 28)),
        "custom_sockets": int(app.storage.tab.get("compute_custom_sockets", 2)),
        "custom_ram_gib": int(app.storage.tab.get("compute_custom_ram", 512)),
    }


def _resolve_host_config(cfg: _ComputeConfig) -> HostConfig:
    """Return HostConfig from session config. Custom preset uses session values."""
    name = str(cfg["preset_name"])
    if name == "Custom" or name not in _PRESET_BY_NAME:
        return HostConfig(
            name="Custom",
            cores_per_socket=cfg["custom_cores_per_socket"],
            sockets=cfg["custom_sockets"],
            ram_gib=cfg["custom_ram_gib"],
        )
    return _PRESET_BY_NAME[name]


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
                ui.label(
                    t("compute.excluded_vms", count=result.excluded_vm_count)
                ).classes("text-sm text-gray-500")


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
        t("compute.constraint_vcpu")
        if result.hosts_by_vcpu >= result.hosts_by_ram
        else t("compute.constraint_ram")
    )
    with ui.card().classes("w-full p-4 gap-2"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("dns", size="1.5rem").classes("text-blue-600")
            ui.label(t("compute.hosts_n1")).classes("font-semibold text-blue-800")
            ui.label(str(result.hosts_n1)).classes("text-3xl font-bold text-blue-700")
        ui.label(t("compute.hosts_n1_detail")).classes("text-sm text-gray-500")
        ui.label(f"{t('compute.binding_constraint')}: {constraint_label}").classes("text-xs text-gray-400")

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


# ---------------------------------------------------------------------------
# Settings panel
# ---------------------------------------------------------------------------


def _render_settings_panel(cfg: _ComputeConfig, refresh_fn) -> None:  # type: ignore[no-untyped-def]
    """Render preset selector, overcommit input, and mode toggles."""
    with ui.card().classes("w-full p-4 gap-4"):
        ui.label(t("compute.host_preset")).classes("font-semibold text-gray-700")

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

        # Custom host spec inputs — only visible when Custom is selected
        with ui.column().classes("w-full gap-2") as custom_inputs:
            custom_inputs.set_visibility(cfg["preset_name"] == "Custom")
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
        app.storage.tab["compute_preset"] = e.value
        custom_inputs.set_visibility(e.value == "Custom")
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

    preset_select.on("update:model-value", _on_preset_change)
    overcommit_input.on("update:model-value", _on_overcommit_change)
    vmsc_switch.on("update:model-value", _on_vmsc_change)
    ap_switch.on("update:model-value", _on_ap_change)
    cps_input.on("update:model-value", _on_custom_cps_change)
    sockets_input.on("update:model-value", _on_custom_sockets_change)
    ram_input.on("update:model-value", _on_custom_ram_change)


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

    with layout("StorePredict - " + t("compute.title")), ui.column().classes(
        "w-full max-w-4xl mx-auto p-4 gap-4"
    ):
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
