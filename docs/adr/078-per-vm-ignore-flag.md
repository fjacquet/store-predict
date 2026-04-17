# ADR-078: Per-VM Ignore Flag — Filter-at-the-Edge Pattern

**Status:** Accepted
**Date:** 2026-04-17
**Issue:** #11 ("Drop selection")

## Context

Pre-sales engineers reviewing a classified VM list sometimes need to exclude specific VMs from the sizing result — decommissioned hosts, templates that slipped past the ingestion filter, or VMs the customer has confirmed are out of scope. Prior to this change, the only way to remove a VM was to go back to the upload/scope step, which clears the entire session and loses the user's classification edits.

Two reasonable designs were available:

1. **In-pipeline skip:** add an `is_ignored` field read inside `calculate()`, skipping flagged rows.
2. **Filter-at-the-edge:** keep `calculate()` unaware; filter `row_data` in the UI layer before every call site (report page, stats cards).

## Decision

Adopt **filter-at-the-edge** (#2). Store `is_ignored: bool` on each session row; the review page filters it out of `build_summary_stats`, and the report page filters it out of `vm_data` before calling `calculate()`. `calculate()`, `generate_report_pdf()`, and `generate_report_xlsx()` remain untouched.

Persistence reuses the existing `save_filtered_rows` merge mechanism — the flag is added to the merge-keys tuple so that edits on a scope-filtered subset correctly merge back into full session storage.

## Consequences

**Positive:**

- Mirrors the established scope-filtering pattern (`load_filtered_session_data` filters datacenter/cluster at the edge, not inside `calculate()`); one mental model for all "exclusion" features.
- No changes required in the calculation pipeline, PDF generator, Excel generator, or their 100+ tests — every downstream consumer automatically respects the flag because it receives an already-filtered list.
- The flag is independent of scope filters: a VM can be out-of-scope (hidden from review entirely) *and/or* ignored (visible on review but excluded from the report). The two operations compose.
- Ignored VMs stay visible on the review page (greyed out via `getRowStyle`), so the user can toggle them back without re-uploading.

**Negative:**

- Two call sites must remember to filter before aggregating: the review page's `build_summary_stats` and the report page's `calculate()` call. A future aggregation added without the filter would silently include ignored VMs. Mitigated by `test_ignore_selection.py` exercising the filter at both edges.

**Neutral:**

- The flag defaults to `False` and is injected via `row.setdefault("is_ignored", False)` on review-page load, so sessions saved before this change restore cleanly.
