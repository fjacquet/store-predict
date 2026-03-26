---
phase: 029-reporting-fidelity
plan: "02"
subsystem: classification
tags: [classification, backup, monitoring, redis, veritas, netbackup, nagios, solarwinds]
dependency_graph:
  requires: []
  provides: [CLASSIF-01, CLASSIF-02, CLASSIF-03]
  affects: [src/store_predict/pipeline/classification.py, tests/test_classification.py]
tech_stack:
  added: []
  patterns: [ClassificationRule priority tiers, _patterns() helper, TDD red-green]
key_files:
  created: []
  modified:
    - src/store_predict/pipeline/classification.py
    - tests/test_classification.py
decisions:
  - "Veritas/NetBackup rule placed at priority 298 (between Commvault at 297 and VM Replication at 300) to maintain proper priority ordering"
  - "BACKUP added to File Archive rule at priority 360 with priority 300 Veeam rule ensuring no false-positive for veeam-backup-* names"
  - "REDIS added to MySQL/NoSQL rule at priority 101 (Database tier) matching existing NoSQL grouping"
  - "Monitoring tools (NAGIOS, ICINGA, SOLARWINDS, LIBRENMS, OPENNMS) added to Logging Analytics rule inline with existing monitoring patterns"
metrics:
  duration: "7 minutes"
  completed_date: "2026-03-26"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 29 Plan 02: Classification Coverage Expansion Summary

**One-liner:** Expanded classification rules for backup tools (Veritas/NetBackup), network monitoring infrastructure (Nagios, SolarWinds, Icinga, LibreNMS, OpenNMS), and Redis database VMs using TDD.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Veritas/NetBackup rule and BACKUP pattern to File Archive | 2926455 | classification.py, test_classification.py |
| 2 | Add monitoring patterns and Redis to existing rules | c166b0d | classification.py, test_classification.py |

## Changes Made

### classification.py

**New rule (priority 298) — Veritas / NetBackup:**
```python
ClassificationRule(
    name="Veritas / NetBackup",
    category="VM Replication",
    subcategory="Veeam, Zerto, RP4VM",
    priority=298,
    vm_name_patterns=_patterns("VERITAS", "NETBACKUP", "NBU"),
),
```

**File Archive rule (priority 360) — added BACKUP:**
```python
vm_name_patterns=_patterns("ARCHIVE", "BACKUP"),
```

**MySQL/NoSQL rule (priority 101) — added REDIS:**
```python
vm_name_patterns=_patterns("MYSQL", "NOSQL", "MARIADB", "FILEMAKER", "CLARIS", "SQLITE", "REDIS"),
```

**Logging Analytics rule (priority 400) — added 5 monitoring tools:**
- NAGIOS (Nagios monitoring platform)
- ICINGA (Icinga monitoring, Nagios fork)
- SOLARWINDS (SolarWinds network monitoring)
- LIBRENMS (LibreNMS open-source network monitoring)
- OPENNMS (OpenNMS open-source network management)

### test_classification.py

Added:
- `test_backup_classification` — 5 parametrized cases: Veritas-Media-01, NetBackup-Master, NBU-Client-03 -> VM Replication; Backup-Server-01 -> File; veeam-backup-01 -> VM Replication (priority ordering verified)
- `test_monitoring_classification` — 5 parametrized cases: Nagios-Monitor, Icinga-Server, SolarWinds-NPM, LibreNMS-Poller, OpenNMS-Core -> Logging - Analytics
- `test_redis_classification` — 1 parametrized case: Redis-Cache-01 -> Database

## Verification Results

- `rtk pytest tests/test_classification.py -x`: 67 passed (no regressions)
- `rtk pytest tests/test_classification.py tests/test_classification_integration.py tests/test_classification_prefix.py -x`: 87 passed
- `rtk ruff check classification.py test_classification.py`: No issues found

## Deviations from Plan

None — plan executed exactly as written.

**Note:** The plan referenced `tests/test_classifier.py` but the actual file is `tests/test_classification.py`. Used the correct existing file.

## Requirements Closed

- CLASSIF-01: Veritas/NetBackup patterns added
- CLASSIF-02: Network monitoring patterns (Nagios, SolarWinds, Icinga, LibreNMS, OpenNMS) added
- CLASSIF-03: Redis pattern added to Database rules

## Self-Check: PASSED

| Item | Status |
|------|--------|
| classification.py exists | FOUND |
| test_classification.py exists | FOUND |
| 029-02-SUMMARY.md exists | FOUND |
| commit 2926455 (Task 1) | FOUND |
| commit c166b0d (Task 2) | FOUND |
