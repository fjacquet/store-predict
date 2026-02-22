# Requirements: StorePredict v4.0

**Defined:** 2026-02-22
**Core Value:** Accurate DRR sizing + optimal datastore layout + compute sizing + environment health checks — all from a static export file with no live vCenter required

## v4.0 Requirements

Requirements for the v4.0 milestone. Each maps to roadmap phases.

### Grid UX (GUX)

- [ ] **GUX-01**: User can search VMs by text across all visible columns using a quick-filter box
- [ ] **GUX-02**: User can toggle column visibility (CPU, RAM, IOPS) via AG Grid sidebar panel

### VM Data (VDAT)

- [ ] **VDAT-01**: User sees vCPU count and RAM (MiB) columns in the VM grid (hidden by default, enabled via sidebar)

### Concerns & Health Checks (HLT)

- [ ] **HLT-01**: User sees data quality findings: VMs missing OS info, zero provisioned storage, missing CPU/RAM data, high powered-off VM ratio
- [ ] **HLT-02**: User sees sizing risk findings: large Unknown VMs inflating estimates, high DRR override count, VMs exceeding datastore IOPS budget
- [ ] **HLT-03**: User sees VMware best practice findings: old VM hardware version, VMs without cluster assignment, VMs with missing VMware Tools status

### Compute Sizing (COMP)

- [ ] **COMP-01**: User sees total vCPU and RAM aggregates derived from uploaded RVTools/LiveOptics data (powered-off VMs and templates excluded with count shown)
- [ ] **COMP-02**: User sees recommended ESXi host count for N+1 HA with configurable vCPU overcommit ratio
- [ ] **COMP-03**: User can toggle vMSC (stretch cluster) mode to see per-site host count (with graceful warning when no datacenter column data is available)
- [ ] **COMP-04**: User can toggle Active/Passive DR mode to see total host count for both primary and secondary sites
- [ ] **COMP-05**: User can select from Dell PowerEdge preset host configurations (R760/R860/R960) or enter custom specs (cores/socket, sockets, RAM per host)

## Future Requirements

Deferred to v4.1+. Tracked but not in current roadmap.

### Classification

- **CLASS-01**: OS-based fallback rules (Windows Server, RHEL, Ubuntu, SUSE) for classifying generic VM names
- **CLASS-02**: Generic app-server VM name patterns (app, web, svc, srv, api) classified as Virtual Machines instead of Unknown

### Grid UX

- **GUX-03**: Workload category filter chips to show only Unknown VMs or filter by workload category
- **GUX-04**: Powered-off/template exclusion toggle in the VM review grid

### Compute Sizing

- **COMP-06**: Per-cluster compute sizing breakdown (requires datacenter/cluster column grouping)
- **COMP-07**: N+2 HA mode (two host failures)

## Out of Scope

| Feature | Reason |
|---------|--------|
| AG Grid replacement | AG Grid Community is deeply integrated; v4.0 adds needed features; switch is a separate architecture decision |
| Snapshot age health checks | RVTools vInfo tab does not contain snapshot metadata — requires vSnapshot tab parser not in scope |
| VMware Tools version health checks | RVTools vInfo does not export version strings with enough precision — requires vTools tab |
| Per-cluster compute sizing | Complex UI grouping; single-cluster aggregation covers most pre-sales scenarios |
| Live vCenter connectivity | Tool is offline-first by design |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUX-01 | — | Pending |
| GUX-02 | — | Pending |
| VDAT-01 | — | Pending |
| HLT-01 | — | Pending |
| HLT-02 | — | Pending |
| HLT-03 | — | Pending |
| COMP-01 | — | Pending |
| COMP-02 | — | Pending |
| COMP-03 | — | Pending |
| COMP-04 | — | Pending |
| COMP-05 | — | Pending |

**Coverage:**
- v4.0 requirements: 11 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 11 ⚠️

---
*Requirements defined: 2026-02-22*
*Last updated: 2026-02-22 after initial v4.0 definition*
