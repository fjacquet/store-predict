# ADR-049: AG Grid v34 circular context — event args filter

**Date:** 2026-02-20
**Status:** Accepted

## Context

After switching to AG Grid Community and implementing `rowClicked` event handling, all
row-click events silently failed to reach Python. Playwright captured this browser error:

```text
TypeError: Converting circular structure to JSON
  --> starting at object with constructor 'Object'
  |     property 'context' -> object with constructor 'Sr'
  --- property 'beans' closes the circle
```

AG Grid v34 injects its internal `GridContext` object (which has a circular `beans`
reference) into `event.context` for all grid events. NiceGUI's `aggrid.js`
`handle_event` passes `args.context` verbatim to `this.$emit()`, and NiceGUI's
`nicegui.js` then attempts `JSON.stringify` of all event fields for socket.io transport,
triggering the circular reference error.

Two mitigations were applied:

1. **Venv patch** — `aggrid.js` line 65 was patched to wrap `args.context` in a
   `try { JSON.parse(JSON.stringify(...)) } catch(e) { return null }` IIFE. This
   prevents the error inside the component but is fragile (venv updates overwrite it).

2. **Event args filter (primary fix)** — NiceGUI's `Element.on()` accepts an `args`
   parameter that tells the JavaScript layer which fields to include in the serialized
   event payload. By specifying only the fields our handlers actually need, `context` is
   never included in the JSON.stringify call.

## Decision

Use explicit `args` lists on all AG Grid event registrations:

```python
grid.on("cellValueChanged", handler, args=["colId", "data", "newValue"])
grid.on("rowClicked",       handler, args=["data", "rowIndex"])
```

This is the primary fix. The venv patch provides defense-in-depth but must not be
relied upon as the sole protection.

## Consequences

- Event handlers receive only the declared fields; any new field needed must be added to
  the `args` list and the `handle_event` extracted properties in `aggrid.js`
- The venv patch to `aggrid.js` must be re-applied after any NiceGUI upgrade; document
  this in the upgrade checklist
- Future AG Grid events added to the codebase must always declare an `args` filter
- This pattern should be considered whenever NiceGUI's `handle_event` is used with
  third-party Vue components that embed complex internal objects in event data
