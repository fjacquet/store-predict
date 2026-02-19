"""Awaitable multi-select workload dialog component."""

from __future__ import annotations

from nicegui import ui


class WorkloadDialog(ui.dialog):
    """Dialog for assigning multiple workload types to a VM.

    Uses the awaitable dialog pattern: call ``result = await dialog``
    to get the selected workloads or ``None`` if cancelled.

    Args:
        vm_name: VM name displayed in the dialog title.
        current_workloads: List of currently selected workload labels.
        all_options: List of dicts with ``label`` and ``value`` keys
            representing available workload choices.
    """

    def __init__(
        self,
        vm_name: str,
        current_workloads: list[str],
        all_options: list[dict[str, object]],
    ) -> None:
        super().__init__()
        self.props("persistent")
        with self, ui.card().classes("w-96"):
            ui.label(f"Workloads for {vm_name}").classes("text-lg font-bold")
            ui.label(
                "Select one or more workload types. Conservative (lowest) DRR will be used."
            ).classes("text-sm text-gray-500")
            self.select = (
                ui.select(
                    options=all_options,
                    multiple=True,
                    value=current_workloads,
                    label="Select workload types",
                )
                .props("use-chips")
                .classes("w-full")
            )
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=lambda: self.submit(None))
                ui.button(
                    "Apply",
                    on_click=lambda: self.submit(self.select.value),
                ).classes("bg-blue-600 text-white")
