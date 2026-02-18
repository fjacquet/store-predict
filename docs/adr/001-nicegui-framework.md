# ADR-001: Use NiceGUI for Web Framework

**Status:** Accepted
**Date:** 2026-02-18

## Context

StorePredict needs a web UI for file upload, data review, and PDF download. The team is Python-focused with no dedicated frontend developers.

## Decision

Use NiceGUI as the web framework.

## Rationale

- Pure Python — no JavaScript/TypeScript build pipeline
- Built-in Tailwind CSS support
- AG Grid integration for data tables
- File upload components included
- Per-session state management built-in
- Active development and good documentation

## Alternatives Considered

- **Streamlit:** Simpler but limited table editing, no AG Grid
- **Dash (Plotly):** More complex, callback-based architecture
- **FastAPI + React:** Requires frontend skills and separate build pipeline

## Consequences

- UI code is tightly coupled to NiceGUI conventions
- Limited customization compared to full frontend frameworks
- Community smaller than Streamlit/Dash
