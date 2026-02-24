# Requirements: StorePredict v7.0

**Defined:** 2026-02-24
**Core Value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required

## v7.0 Requirements

Requirements for the Save & Restore + Concerns milestone. Each maps to roadmap phases.

### Session Persistence

- [x] **SAVE-01**: User can save the current session to a .zip archive (contains original uploaded file + JSON state)
- [x] **SAVE-02**: The .zip archive captures VM list, workload classifications, DRR overrides, layout settings, and compute settings
- [x] **SAVE-03**: User can restore a session from a .zip file via the Upload page
- [x] **SAVE-04**: After restore, the tool lands on the Upload page with all VM data, classifications, and settings loaded — same state as when saved
- [x] **SAVE-05**: Save and restore are available regardless of which input format was used (RVTools, LiveOptics xlsx, LiveOptics csv, dual-source merge)

### Concerns Enhancements

- [x] **CONC-01**: Each health finding on /concerns displays an actionable remediation hint explaining what to do about the issue
- [ ] **CONC-02**: User can export the /concerns page as a standalone PDF report
- [ ] **CONC-03**: User can export the /concerns page as a standalone CSV file with all findings and remediation hints

## Future Requirements

Features acknowledged but deferred to v8.0 or later.

### Session Management

- **SESS-01**: User can attach customer name and opportunity ID to a saved session
- **SESS-02**: Auto-save session to browser localStorage periodically
- **SESS-03**: Named project library with browse/delete interface

### Concerns

- **CONC-04**: User can filter /concerns by severity (Critical / Warning / Info)
- **CONC-05**: User can configure custom thresholds for health check triggers

## Out of Scope

Explicitly excluded to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Browser auto-save (localStorage) | File-based save is more explicit and portable |
| Server-side project library | File-based approach is simpler; users manage files in filesystem |
| Custom concern thresholds | Adds complexity; standard VMware best-practice thresholds cover most cases |
| Severity filtering on /concerns | Current scannable page is sufficient; deferred to v8+ |
| Session merge with fresh upload | High complexity, edge cases; file-based restore is clear and simple |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAVE-01 | Phase 27 | Complete |
| SAVE-02 | Phase 27 | Complete |
| SAVE-03 | Phase 27 | Complete |
| SAVE-04 | Phase 27 | Complete |
| SAVE-05 | Phase 27 | Complete |
| CONC-01 | Phase 28 | Complete |
| CONC-02 | Phase 28 | Pending |
| CONC-03 | Phase 28 | Pending |

**Coverage:**
- v7.0 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 after initial definition*
