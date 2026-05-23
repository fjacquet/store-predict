"""Compute Sizing page — redirects to PreSizion for advanced compute sizing."""

from __future__ import annotations

from nicegui import ui

from store_predict.i18n import t
from store_predict.ui.layout import layout

PRESIZION_URL = "https://fjacquet.github.io/presizion/"
PRESIZION_REPO = "https://github.com/fjacquet/presizion"


@ui.page("/compute")
async def compute_page() -> None:
    """Compute Sizing page — link to PreSizion project."""
    await ui.context.client.connected()

    with (
        layout("StorePredict - " + t("compute.title")),
        ui.column().classes("w-full max-w-2xl mx-auto p-8 gap-6 items-center"),
    ):
        ui.label(t("compute.title")).classes("text-2xl font-bold sp-display")
        ui.separator()

        with ui.card().classes("p-8 gap-4 items-center text-center"):
            ui.icon("open_in_new", size="3rem").style("color:var(--sp-primary)")
            ui.label(t("compute.redirect_message")).classes("text-lg max-w-lg").style("color:var(--sp-muted)")
            ui.link(
                t("compute.open_presizion"),
                PRESIZION_URL,
                new_tab=True,
            ).classes("text-lg font-semibold px-6 py-3 rounded-lg no-underline").props("color=primary")
            ui.link(
                t("compute.view_source"),
                PRESIZION_REPO,
                new_tab=True,
            ).classes("text-sm no-underline hover:underline mt-2").style("color:var(--sp-primary)")
