# ADR-051: LLM → keyword extraction → rule suggestion feedback loop

**Date:** 2026-02-20
**Status:** Accepted

## Context

The LLM classifier handles VMs that the deterministic rule engine cannot classify. Each
LLM call costs latency and API credits. Over time, recurring patterns in LLM-classified
VMs represent opportunities for new deterministic rules that would eliminate future LLM
calls and improve consistency.

## Decision

Extend `classify_single_vm` to return a `(category, keyword | None)` tuple by prompting
the LLM with:

```text
Respond with EXACTLY this format: Category|KEYWORD
KEYWORD = one short UPPERCASE word (max 12 chars) extracted from the VM name that most
strongly identifies the workload. Use NONE if no clear keyword exists.
```

`classify_unknown_vms_async` aggregates keywords across all LLM-classified VMs into
`RuleSuggestion` dataclass instances (keyword, category, subcategory, vm_examples,
count). These are persisted to tab storage and rendered in a "Proposed Rules" panel on
the review page as copy-pasteable `ClassificationRule(...)` snippets.

## Consequences

- LLM prompt is more constrained (structured output `Category|KEYWORD` instead of free
  text) — minor risk of format deviation; parser falls back gracefully if the pipe
  separator is absent
- `classify_unknown_vms_async` return type changed from `list[dict]` to
  `tuple[list[dict], list[RuleSuggestion]]` — all callers updated
- Suggestions are advisory only; the rule engine is not modified at runtime; the user
  copies snippets into `classification.py` manually
- No additional LLM tokens consumed; the keyword is extracted from the same response
  that contains the category
- `RuleSuggestion` objects are stored in tab storage (serialized as dicts) and survive
  page navigation within a session but not across server restarts
