# ADR-068: Remediation hints as hardcoded English strings

**Date:** 2026-02-24
**Status:** Accepted

## Context

The `/concerns` page displays health findings (e.g., "Missing OS names",
"VMware Tools not installed"). Each finding needs an actionable hint
explaining what to do about the issue (CONC-01).

StorePredict supports FR/EN internationalization via `t()` and YAML locale
files. The question is whether remediation hint strings should go through the
i18n pipeline.

## Decision

Remediation hints are stored as hardcoded English strings in a `remediation`
field on the `HealthFinding` dataclass, populated directly in each check
function in `pipeline/health_checks.py`. They are **not** run through `t()`.

## Rationale

- **Audience:** The `/concerns` page is an engineering document, not a
  customer-facing output. The PDF findings appendix is also generated in
  English (described in ADR-069). Pre-sales engineers using the French locale
  read English technical documentation.
- **Maintenance cost:** Keeping FR/EN translations in sync for 14 finding
  types across two YAML files adds overhead with minimal user benefit.
- **Precedent:** VMware, Dell, and most infrastructure tools deliver
  technical remediation guidance in English regardless of UI locale.
- **Extensibility:** The `locale` parameter is reserved on
  `generate_concerns_pdf()` for future i18n if the requirement arises.

## Consequences

- **Positive:** Hints can be written and updated without touching YAML locale
  files; 14 strings in one file.
- **Positive:** Engineers see the same wording in the UI and in the exported
  PDF regardless of locale setting.
- **Negative:** French-locale users see English hint text in what is otherwise
  a French-language UI. Acceptable given the engineering audience.
- **Future:** If FR remediation hints are required, the `HealthFinding.remediation`
  field can be changed to `dict[str, str]` (keyed by locale) with a
  `locale`-aware accessor, and `generate_concerns_pdf()` can begin using
  its reserved `locale` parameter.
