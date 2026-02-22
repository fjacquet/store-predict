# ADR-063: TypedDict for NiceGUI page session config dicts

**Date:** 2026-02-22
**Status:** Accepted

## Context

NiceGUI page functions read user preferences from `app.storage.tab` (tab-scoped
storage) and assemble them into a dict that is passed to helpers like
`_render_settings_panel()` and `_results_panel()`. The initial implementation
annotated this dict as `dict[str, object]`, which caused Pyright to report
`reportArgumentType` errors wherever values were used as `int`, `float`, or
`bool` — because `object` is not assignable to `ConvertibleToInt` etc.

## Decision

Define a `TypedDict` subclass (`_ComputeConfig`) for each page's session config
dict. Helper functions receive and return the typed dict.

```python
class _ComputeConfig(TypedDict):
    preset_name: str
    overcommit_ratio: float
    vmsc_enabled: bool
    ap_enabled: bool
    custom_cores_per_socket: int
    custom_sockets: int
    custom_ram_gib: int

def _load_compute_config() -> _ComputeConfig: ...
def _resolve_host_config(cfg: _ComputeConfig) -> HostConfig: ...
```

`_load_compute_config()` already coerces values at read time (`int(...)`,
`float(...)`, `bool(...)`), so the TypedDict is accurate.

## Rationale

`TypedDict` is the standard Python mechanism for typed heterogeneous dicts. It
eliminates `int(str(cfg["..."]))` workarounds throughout the function, which were
themselves flagged by Pyright as redundant. The prefix `_` keeps the TypedDict
module-private to the page file.

## Consequences

- **Positive:** All session config accesses are Pyright-clean with no `# type: ignore`.
- **Positive:** Values can be used directly (`cfg["overcommit_ratio"]`) without
  redundant casts.
- **Positive:** Dict structure is self-documenting via the TypedDict definition.
- **Negative:** One TypedDict per page is boilerplate, but it is small and local.
- **Pattern:** Apply to all future NiceGUI pages that assemble session dicts.
