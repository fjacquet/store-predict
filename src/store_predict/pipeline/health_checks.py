"""Health check engine for session DataFrame quality and best-practice analysis.

Pure pipeline module with zero UI imports. Entry point: run_health_checks(df).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

__all__ = [
    "HealthCheckResult",
    "HealthFinding",
    "Severity",
    "run_health_checks",
]


# ---------------------------------------------------------------------------
# Thresholds (constants at module level for easy review)
# ---------------------------------------------------------------------------

_POWERED_OFF_RATIO_THRESHOLD = 0.30  # >30% powered-off -> Info finding
_UNKNOWN_RATIO_THRESHOLD = 0.25  # >25% Unknown active VMs -> Warning
_LARGE_VM_THRESHOLD_MIB = 1024 * 1024  # 1 TiB in MiB
_IOPS_BUDGET_PER_DS = 100_000.0  # Standard Dell datastore IOPS budget
_OLD_HW_VERSION = 17  # vHW 17 = ESXi 7.0 -- minimum recommended
_VERY_OLD_HW_VERSION = 14  # vHW 14 = ESXi 6.7 -- critical threshold


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class Severity(StrEnum):
    """Finding severity levels."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class HealthFinding:
    """A single health concern with severity and context.

    title and detail are i18n keys -- callers pass them to t() for display.
    affected_vms contains raw VM names for UI display ONLY -- never log these.
    """

    check_id: str  # e.g. "data_quality.zero_provisioned"
    severity: Severity
    title: str  # i18n key, e.g. "health.zero_provisioned.title"
    detail: str  # i18n key, e.g. "health.zero_provisioned.detail"
    affected_count: int  # Number of VMs triggering this finding
    affected_vms: tuple[str, ...]  # Sample VM names (max 5, for display only)
    cluster: str = ""  # Cluster name for per-cluster findings; empty for global findings


@dataclass(frozen=True)
class HealthCheckResult:
    """Aggregated findings from all health checks."""

    findings: tuple[HealthFinding, ...]
    total_vms_checked: int
    has_data: bool  # False if session is empty -- page shows "no data" state

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_health_checks(df: pd.DataFrame | None) -> HealthCheckResult:
    """Run all health checks on the session DataFrame.

    Args:
        df: Canonical DataFrame from load_session_data(), or None if no data uploaded.
            Must include is_powered_on, is_template, hw_version, tools_status columns.
            hw_version sentinel: 0 means data not available (LiveOptics or old RVTools).

    Returns:
        HealthCheckResult with all findings. Returns has_data=False if df is None or empty.
    """
    if df is None or df.empty:
        return HealthCheckResult(findings=(), total_vms_checked=0, has_data=False)

    # ALWAYS filter before checks -- only powered-on, non-template VMs for best-practice checks
    active = df[(df["is_powered_on"] == True) & (df["is_template"] == False)]  # noqa: E712

    findings: list[HealthFinding] = []

    # Data quality checks (HLT-01)
    findings.extend(_check_missing_os(active))
    findings.extend(_check_zero_provisioned(active))
    findings.extend(_check_missing_cpu(active))
    findings.extend(_check_missing_ram(active))
    findings.extend(_check_high_powered_off_ratio(df, active))

    # Sizing risk checks (HLT-02)
    findings.extend(_check_high_unknown_ratio(active))
    findings.extend(_check_large_unknown_vms(active))
    findings.extend(_check_iops_budget_exceeded(active))

    # VMware best practice checks (HLT-03)
    findings.extend(_check_no_cluster(active))
    findings.extend(_check_hw_version_per_cluster(active))
    findings.extend(_check_small_cluster_ha(active))
    findings.extend(_check_tools_status(active))

    return HealthCheckResult(
        findings=tuple(findings),
        total_vms_checked=len(active),
        has_data=True,
    )


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------


def _check_missing_os(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag active VMs with empty OS name string."""
    mask = df["os_name"].fillna("").astype(str).str.strip() == ""
    bad = df[mask]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="data_quality.missing_os",
            severity=Severity.WARNING,
            title="health.missing_os.title",
            detail="health.missing_os.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_zero_provisioned(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag active VMs with zero provisioned storage."""
    prov = pd.to_numeric(df["provisioned_mib"], errors="coerce").fillna(0)
    bad = df[prov == 0]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="data_quality.zero_provisioned",
            severity=Severity.WARNING,
            title="health.zero_provisioned.title",
            detail="health.zero_provisioned.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_missing_cpu(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag active VMs with zero vCPU count."""
    cpus = pd.to_numeric(df["num_cpus"], errors="coerce").fillna(0)
    bad = df[cpus == 0]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="data_quality.missing_cpu",
            severity=Severity.INFO,
            title="health.missing_cpu.title",
            detail="health.missing_cpu.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_missing_ram(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag active VMs with zero RAM."""
    ram = pd.to_numeric(df["memory_mib"], errors="coerce").fillna(0)
    bad = df[ram == 0]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="data_quality.missing_ram",
            severity=Severity.INFO,
            title="health.missing_ram.title",
            detail="health.missing_ram.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_high_powered_off_ratio(full_df: pd.DataFrame, _active: pd.DataFrame) -> list[HealthFinding]:
    """Flag environments where >30% of VMs are powered off (stale data signal)."""
    total = len(full_df)
    if total == 0:
        return []
    powered_off_count = len(full_df[full_df["is_powered_on"] == False])  # noqa: E712
    ratio = powered_off_count / total
    if ratio <= _POWERED_OFF_RATIO_THRESHOLD:
        return []
    return [
        HealthFinding(
            check_id="data_quality.high_powered_off_ratio",
            severity=Severity.INFO,
            title="health.high_powered_off_ratio.title",
            detail="health.high_powered_off_ratio.detail",
            affected_count=powered_off_count,
            affected_vms=(),
        )
    ]


def _check_high_unknown_ratio(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag environments where >25% of active VMs are classified as Unknown."""
    total = len(df)
    if total == 0:
        return []
    unknown_mask = df["workload_category"].fillna("").astype(str).str.startswith("Unknown")
    unknown_count = unknown_mask.sum()
    ratio = unknown_count / total
    if ratio <= _UNKNOWN_RATIO_THRESHOLD:
        return []
    return [
        HealthFinding(
            check_id="sizing_risk.high_unknown_ratio",
            severity=Severity.WARNING,
            title="health.high_unknown_ratio.title",
            detail="health.high_unknown_ratio.detail",
            affected_count=int(unknown_count),
            affected_vms=tuple(df[unknown_mask]["vm_name"].head(5).tolist()),
        )
    ]


def _check_large_unknown_vms(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag Unknown VMs larger than 1 TiB provisioned storage."""
    unknown_mask = df["workload_category"].fillna("").astype(str).str.startswith("Unknown")
    prov = pd.to_numeric(df["provisioned_mib"], errors="coerce").fillna(0)
    large_mask = prov >= _LARGE_VM_THRESHOLD_MIB
    bad = df[unknown_mask & large_mask]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="sizing_risk.large_unknown_vms",
            severity=Severity.WARNING,
            title="health.large_unknown_vms.title",
            detail="health.large_unknown_vms.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_iops_budget_exceeded(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag VMs whose peak_iops exceeds the standard 100K/datastore budget."""
    iops = pd.to_numeric(df["peak_iops"], errors="coerce").fillna(0)
    bad = df[(iops > 0) & (iops > _IOPS_BUDGET_PER_DS)]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="sizing_risk.iops_budget_exceeded",
            severity=Severity.WARNING,
            title="health.iops_budget_exceeded.title",
            detail="health.iops_budget_exceeded.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_no_cluster(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag active VMs not assigned to a cluster."""
    bad = df[df["cluster"].fillna("").astype(str).str.strip() == ""]
    if bad.empty:
        return []
    return [
        HealthFinding(
            check_id="best_practice.no_cluster",
            severity=Severity.WARNING,
            title="health.no_cluster.title",
            detail="health.no_cluster.detail",
            affected_count=len(bad),
            affected_vms=tuple(bad["vm_name"].head(5).tolist()),
        )
    ]


def _check_hw_version(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag VMs with old VMware hardware version.

    CRITICAL sentinel guard: hw_version == 0 means data not available
    (LiveOptics exports or RVTools without HW version column).
    Never flag sentinel 0 as old hardware.

    # Superseded by _check_hw_version_per_cluster() — kept as private helper
    """
    hw = pd.to_numeric(df.get("hw_version", pd.Series([0] * len(df))), errors="coerce").fillna(0).astype(int)

    # Skip entire check if no HW version data in this export
    if (hw > 0).sum() == 0:
        return []

    findings: list[HealthFinding] = []

    # Very old: below vHW 14 (ESXi 6.7) -- Critical
    very_old_mask = (hw > 0) & (hw < _VERY_OLD_HW_VERSION)
    very_old = df[very_old_mask]
    if not very_old.empty:
        findings.append(
            HealthFinding(
                check_id="best_practice.very_old_hw_version",
                severity=Severity.CRITICAL,
                title="health.very_old_hw_version.title",
                detail="health.very_old_hw_version.detail",
                affected_count=len(very_old),
                affected_vms=tuple(very_old["vm_name"].head(5).tolist()),
            )
        )
    else:
        # Only check "old" (14-16) if none are "very old" to avoid duplicate findings
        old_mask = (hw > 0) & (hw >= _VERY_OLD_HW_VERSION) & (hw < _OLD_HW_VERSION)
        old = df[old_mask]
        if not old.empty:
            findings.append(
                HealthFinding(
                    check_id="best_practice.old_hw_version",
                    severity=Severity.WARNING,
                    title="health.old_hw_version.title",
                    detail="health.old_hw_version.detail",
                    affected_count=len(old),
                    affected_vms=tuple(old["vm_name"].head(5).tolist()),
                )
            )

    return findings


def _check_hw_version_per_cluster(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag VMs with old VMware hardware version, grouped by cluster.

    Emits one finding per affected cluster so the UI can show which clusters
    have outdated hardware. CRITICAL sentinel guard: hw_version == 0 means
    data not available — never flag sentinel 0 as old hardware.
    """
    hw = pd.to_numeric(df.get("hw_version", pd.Series([0] * len(df))), errors="coerce").fillna(0).astype(int)

    # Skip entire check if no HW version data in this export
    if (hw > 0).sum() == 0:
        return []

    df_work = df.copy()
    df_work["_hw"] = hw

    # Normalize cluster column for groupby labeling (do NOT log cluster names)
    cluster_col = df_work["cluster"].fillna("").astype(str).str.strip().replace("", "(No Cluster)")
    df_work["_cluster_label"] = cluster_col

    findings: list[HealthFinding] = []
    for cluster_name, group in df_work.groupby("_cluster_label", sort=True):
        group_hw = group["_hw"]

        # Skip if no HW data for this cluster
        if (group_hw > 0).sum() == 0:
            continue

        # Very old: below vHW 14 (ESXi 6.7) -- Critical
        very_old_mask = (group_hw > 0) & (group_hw < _VERY_OLD_HW_VERSION)
        if very_old_mask.any():
            findings.append(
                HealthFinding(
                    check_id="best_practice.very_old_hw_version",
                    severity=Severity.CRITICAL,
                    title="health.very_old_hw_version.title",
                    detail="health.very_old_hw_version.detail",
                    affected_count=len(group[very_old_mask]),
                    affected_vms=tuple(group[very_old_mask]["vm_name"].head(5).tolist()),
                    cluster=str(cluster_name),
                )
            )
        else:
            # Only check "old" (14-16) if none are "very old"
            old_mask = (group_hw > 0) & (group_hw >= _VERY_OLD_HW_VERSION) & (group_hw < _OLD_HW_VERSION)
            if old_mask.any():
                findings.append(
                    HealthFinding(
                        check_id="best_practice.old_hw_version",
                        severity=Severity.WARNING,
                        title="health.old_hw_version.title",
                        detail="health.old_hw_version.detail",
                        affected_count=len(group[old_mask]),
                        affected_vms=tuple(group[old_mask]["vm_name"].head(5).tolist()),
                        cluster=str(cluster_name),
                    )
                )

    return findings


def _check_small_cluster_ha(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag clusters with fewer than 3 VMs as at-risk for N+1 HA.

    Standalone hosts (empty/no cluster) are skipped — HA context doesn't apply.
    Emits one finding per affected named cluster.
    """
    # Normalize cluster column — skip VMs without cluster assignment
    cluster_col = df["cluster"].fillna("").astype(str).str.strip()
    df_work = df.copy()
    df_work["_cluster_label"] = cluster_col.replace("", "(No Cluster)")

    findings: list[HealthFinding] = []
    for cluster_name, group in df_work.groupby("_cluster_label", sort=True):
        # Skip standalone hosts — no HA context
        if str(cluster_name) == "(No Cluster)":
            continue

        if len(group) < 3:
            findings.append(
                HealthFinding(
                    check_id="best_practice.small_cluster_ha",
                    severity=Severity.WARNING,
                    title="health.small_cluster_ha.title",
                    detail="health.small_cluster_ha.detail",
                    affected_count=len(group),
                    affected_vms=tuple(group["vm_name"].head(5).tolist()),
                    cluster=str(cluster_name),
                )
            )

    return findings


def _check_tools_status(df: pd.DataFrame) -> list[HealthFinding]:
    """Flag VMs with VMware Tools not installed or not running."""
    status = df["tools_status"].fillna("").astype(str)

    # Skip check if no tools status data (all empty -- LiveOptics or old RVTools)
    has_data = (status != "").any()
    if not has_data:
        return []

    findings: list[HealthFinding] = []

    not_installed = df[status == "toolsNotInstalled"]
    if not not_installed.empty:
        findings.append(
            HealthFinding(
                check_id="best_practice.tools_not_installed",
                severity=Severity.CRITICAL,
                title="health.tools_not_installed.title",
                detail="health.tools_not_installed.detail",
                affected_count=len(not_installed),
                affected_vms=tuple(not_installed["vm_name"].head(5).tolist()),
            )
        )

    not_running = df[status == "toolsNotRunning"]
    if not not_running.empty:
        findings.append(
            HealthFinding(
                check_id="best_practice.tools_not_running",
                severity=Severity.WARNING,
                title="health.tools_not_running.title",
                detail="health.tools_not_running.detail",
                affected_count=len(not_running),
                affected_vms=tuple(not_running["vm_name"].head(5).tolist()),
            )
        )

    return findings
