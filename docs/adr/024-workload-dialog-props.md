# ADR-024: WorkloadDialog Persistent + use-chips Props

**Status:** Accepted
**Date:** 2026-02-19

## Context

The multi-workload assignment dialog must stay open while the user selects multiple workload types. NiceGUI's default dialog and select widget behaviours work against this requirement.

## Decision

Apply `persistent` to the dialog and `use-chips` to the `ui.select` widget inside it.

## Rationale

- `persistent` prevents dismissal on backdrop click, ensuring users do not lose their selections accidentally
- `use-chips` prevents the Quasar select dropdown from closing after each selection, enabling multiple choices without reopening the dropdown each time
- Both properties are Quasar pass-through props supported by NiceGUI

## Alternatives Considered

- **Custom JavaScript overlay:** Full control but requires maintaining JS code alongside Python; high maintenance cost

## Consequences

- Workaround for NiceGUI issue #1108; should be reviewed if NiceGUI adds native multi-select support
- Users must click an explicit confirm button to close the dialog; there is no implicit close gesture
