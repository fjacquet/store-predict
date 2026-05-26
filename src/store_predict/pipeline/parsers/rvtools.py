"""Parser for RVTools xlsx exports."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from store_predict.pipeline.errors import IngestionError
from store_predict.pipeline.models import FileFormat
from store_predict.pipeline.parsers.columns import (
    CANONICAL_COLUMNS,
    REQUIRED_RVTOOLS_COLUMNS,
    REQUIRED_RVTOOLS_VDATASTORE_COLUMNS,
    REQUIRED_RVTOOLS_VDISK_COLUMNS,
    REQUIRED_RVTOOLS_VPARTITION_COLUMNS,
    RVTOOLS_ALIASES,
    RVTOOLS_VDATASTORE_ALIASES,
    RVTOOLS_VDISK_ALIASES,
    RVTOOLS_VPARTITION_ALIASES,
    resolve_columns,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RvtoolsCapacityInfo:
    """Diagnostics from the guest-level capacity basis (for logging / notice)."""

    total_vms: int
    fallback_count: int  # VMs that fell back to the raw vInfo value
    vsan_vm_count: int  # VMs whose home datastore is vSAN (notice only)
    pre_provisioned_mib: float  # sum of vInfo Provisioned (datastore footprint)
    post_provisioned_mib: float  # sum after guest-level recompute
    post_in_use_mib: float

    @property
    def changed(self) -> bool:
        """True when the recompute materially altered the provisioned total."""
        return abs(self.post_provisioned_mib - self.pre_provisioned_mib) > 1.0


def parse_rvtools(path: Path) -> pd.DataFrame:
    """Parse an RVTools xlsx export into a canonical DataFrame.

    Reads the 'vInfo' sheet and normalizes columns to the canonical schema.

    Args:
        path: Path to the RVTools .xlsx file.

    Returns:
        DataFrame with CANONICAL_COLUMNS columns.

    Raises:
        IngestionError: If the file cannot be parsed or required columns are missing.
    """
    try:
        df = pd.read_excel(path, sheet_name="vInfo", engine="openpyxl")
    except (KeyError, ValueError) as exc:
        raise IngestionError(
            f"Cannot read RVTools file: {path.name}. Expected an xlsx file with a 'vInfo' sheet.",
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise IngestionError(
            f"Failed to open file: {path.name}. Is it a valid Excel file?",
            details=str(exc),
        ) from exc

    # Strip column whitespace before resolution
    df.columns = df.columns.str.strip()

    col_map = resolve_columns(df, RVTOOLS_ALIASES, REQUIRED_RVTOOLS_COLUMNS)

    # Build canonical DataFrame
    result = pd.DataFrame()
    result["vm_name"] = df[col_map["vm_name"]].fillna("")
    result["os_name"] = df[col_map["os_name"]].fillna("")
    result["num_cpus"] = (
        pd.to_numeric(df[col_map["num_cpus"]], errors="coerce").fillna(0).astype(int) if col_map.get("num_cpus") else 0
    )
    result["memory_mib"] = (
        pd.to_numeric(df[col_map["memory_mib"]], errors="coerce").fillna(0.0) if col_map.get("memory_mib") else 0.0
    )
    result["provisioned_mib"] = pd.to_numeric(df[col_map["provisioned_mib"]], errors="coerce").fillna(0.0)
    result["in_use_mib"] = pd.to_numeric(df[col_map["in_use_mib"]], errors="coerce").fillna(0.0)

    # Optional columns
    if col_map.get("datacenter"):
        result["datacenter"] = df[col_map["datacenter"]].fillna("")
    else:
        result["datacenter"] = ""

    if col_map.get("cluster"):
        result["cluster"] = df[col_map["cluster"]].fillna("")
    else:
        result["cluster"] = ""

    # is_template: NaN handled as False (research pitfall 1)
    if col_map.get("is_template"):
        result["is_template"] = df[col_map["is_template"]].fillna(False).astype(bool)
    else:
        result["is_template"] = False

    # is_powered_on: derived from powerstate column
    if col_map.get("powerstate"):
        result["is_powered_on"] = df[col_map["powerstate"]].fillna("").astype(str).str.lower() == "poweredon"
    else:
        result["is_powered_on"] = True

    result["source_format"] = FileFormat.RVTOOLS.value

    # Description from Annotation column (optional)
    if col_map.get("vm_description"):
        result["vm_description"] = df[col_map["vm_description"]].fillna("")
    else:
        result["vm_description"] = ""

    # vCenter folder path (optional, used as classifier signal)
    if col_map.get("vm_folder"):
        result["vm_folder"] = df[col_map["vm_folder"]].fillna("").astype(str)
    else:
        result["vm_folder"] = ""

    # hw_version: integer vmx level, 0 if column absent or unreadable
    if col_map.get("hw_version"):
        result["hw_version"] = pd.to_numeric(df[col_map["hw_version"]], errors="coerce").fillna(0).astype(int)
    else:
        result["hw_version"] = 0

    # tools_status: string, empty string if column absent
    if col_map.get("tools_status"):
        result["tools_status"] = df[col_map["tools_status"]].fillna("").astype(str)
    else:
        result["tools_status"] = ""

    # Performance columns not available in RVTools -- default to NaN
    for perf_col in [
        "peak_iops",
        "avg_iops",
        "peak_throughput_mbs",
        "avg_throughput_mbs",
        "peak_latency_ms",
        "avg_read_latency_ms",
        "avg_write_latency_ms",
        "iops_8k_equivalent",
    ]:
        result[perf_col] = float("nan")

    result["row_index"] = 0  # placeholder; overwritten by ingest_file after reset_index

    # Recompute provisioned/in_use from the guest-level view (FTT-free, mount-aware).
    result, cap_info = _apply_guest_capacity_basis(result, df, col_map, path)
    if cap_info.changed or cap_info.vsan_vm_count:
        logger.info(
            "RVTools guest-level capacity basis: provisioned %.1f TiB -> %.1f TiB, "
            "in_use %.1f TiB; vSAN VMs=%d; vInfo-fallback VMs=%d/%d",
            cap_info.pre_provisioned_mib / 1024 / 1024,
            cap_info.post_provisioned_mib / 1024 / 1024,
            cap_info.post_in_use_mib / 1024 / 1024,
            cap_info.vsan_vm_count,
            cap_info.fallback_count,
            cap_info.total_vms,
        )

    out = result[CANONICAL_COLUMNS]
    out.attrs["rvtools_capacity_info"] = cap_info
    return out


def _sum_per_vm(
    path: Path,
    sheet: str,
    aliases: dict[str, list[str]],
    required: set[str],
    value_cols: list[str],
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]] | None:
    """Read an RVTools sheet and sum ``value_cols`` per VM.

    Returns ``(by_uuid, by_name)`` where each maps ``value_col -> {key: sum}``,
    or None if the sheet is missing/unreadable. Joining prefers ``VM UUID`` and
    falls back to ``VM`` name. A key's presence (even with a 0 sum) means the VM
    appears in the sheet.
    """
    try:
        sdf = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    except (KeyError, ValueError):
        return None
    except Exception:
        return None

    sdf.columns = sdf.columns.str.strip()
    try:
        col_map = resolve_columns(sdf, aliases, required)
    except IngestionError:
        return None

    n = len(sdf)
    uuid = sdf[col_map["vm_uuid"]].astype(str).str.strip() if col_map.get("vm_uuid") else pd.Series([""] * n)
    name = sdf[col_map["vm_name"]].astype(str).str.strip() if col_map.get("vm_name") else pd.Series([""] * n)

    by_uuid: dict[str, dict[str, float]] = {}
    by_name: dict[str, dict[str, float]] = {}
    for col in value_cols:
        series = (
            pd.to_numeric(sdf[col_map[col]], errors="coerce").fillna(0.0) if col_map.get(col) else pd.Series([0.0] * n)
        )
        by_uuid[col] = {str(k): float(v) for k, v in series.groupby(uuid).sum().items()}
        by_name[col] = {str(k): float(v) for k, v in series.groupby(name).sum().items()}
    return by_uuid, by_name


def _lookup(
    agg: tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]] | None,
    col: str,
    uuid: str,
    name: str,
) -> tuple[float, bool]:
    """Return ``(value, found)`` for a VM from a :func:`_sum_per_vm` result."""
    if agg is None:
        return 0.0, False
    by_uuid, by_name = agg
    if uuid and uuid in by_uuid.get(col, {}):
        return by_uuid[col][uuid], True
    if name and name in by_name.get(col, {}):
        return by_name[col][name], True
    return 0.0, False


def _read_vsan_datastores(path: Path) -> set[str]:
    """Return the set of vSAN datastore names from the vDatastore sheet (notice only)."""
    try:
        ddf = pd.read_excel(path, sheet_name="vDatastore", engine="openpyxl")
    except Exception:
        return set()
    ddf.columns = ddf.columns.str.strip()
    try:
        col_map = resolve_columns(ddf, RVTOOLS_VDATASTORE_ALIASES, REQUIRED_RVTOOLS_VDATASTORE_COLUMNS)
    except IngestionError:
        return set()
    mask = ddf[col_map["type"]].astype(str).str.lower().str.contains("vsan", na=False)
    return set(ddf.loc[mask, col_map["name"]].astype(str).str.strip())


def _apply_guest_capacity_basis(
    result: pd.DataFrame,
    vinfo_df: pd.DataFrame,
    col_map: dict[str, str | None],
    path: Path,
) -> tuple[pd.DataFrame, RvtoolsCapacityInfo]:
    """Recompute ``provisioned_mib`` / ``in_use_mib`` from the guest-level view.

    On vSAN, ``vInfo.Provisioned MiB`` includes FTT/mirror overhead and misses
    guest-mounted volumes (e.g. Kubernetes PVs). The guest view fixes both:

      provisioned = max(Σ vPartition.Capacity, vmdk_logical)   # both FTT-free
      in_use      = Σ vPartition.Consumed (when guest data exists)

    where ``vmdk_logical`` is ``vInfo.Total disk capacity MiB`` (newer RVTools)
    or Σ ``vDisk.Capacity MiB`` (older). VMs with neither guest data nor disk
    capacity fall back to the raw vInfo values. ``in_use`` is capped at
    ``provisioned``. Rows in ``result`` are positionally aligned with ``vinfo_df``.
    """
    n = len(result)
    uuid_col = col_map.get("vm_uuid")
    uuids = vinfo_df[uuid_col].astype(str).str.strip().tolist() if uuid_col else [""] * n
    names = result["vm_name"].astype(str).str.strip().tolist()

    td_col = col_map.get("total_disk_capacity_mib")
    vmdk_logical_vinfo = pd.to_numeric(vinfo_df[td_col], errors="coerce").fillna(0.0).tolist() if td_col else [0.0] * n

    vpart = _sum_per_vm(
        path,
        "vPartition",
        RVTOOLS_VPARTITION_ALIASES,
        REQUIRED_RVTOOLS_VPARTITION_COLUMNS,
        ["capacity_mib", "consumed_mib"],
    )
    vdisk = _sum_per_vm(
        path,
        "vDisk",
        RVTOOLS_VDISK_ALIASES,
        REQUIRED_RVTOOLS_VDISK_COLUMNS,
        ["capacity_mib"],
    )

    prov_orig = result["provisioned_mib"].tolist()
    inuse_orig = result["in_use_mib"].tolist()
    new_prov: list[float] = []
    new_inuse: list[float] = []
    fallback = 0

    for i in range(n):
        uuid, name = uuids[i], names[i]
        guest_cap, has_part = _lookup(vpart, "capacity_mib", uuid, name)
        guest_used, _ = _lookup(vpart, "consumed_mib", uuid, name)

        vmdk_logical = vmdk_logical_vinfo[i]
        if vmdk_logical <= 0.0:
            vmdk_logical, _ = _lookup(vdisk, "capacity_mib", uuid, name)

        candidate = max(guest_cap, vmdk_logical)
        if candidate > 0.0:
            prov = candidate
        else:
            prov = prov_orig[i]  # no guest data and no disk capacity
            fallback += 1

        used = guest_used if has_part else inuse_orig[i]
        used = min(used, prov)  # in_use can never exceed provisioned

        new_prov.append(prov)
        new_inuse.append(used)

    result["provisioned_mib"] = new_prov
    result["in_use_mib"] = new_inuse

    # vSAN VM count (home-datastore heuristic) — for the user-facing notice only.
    vsan_count = 0
    vsan = _read_vsan_datastores(path)
    path_col = col_map.get("vm_path")
    if vsan and path_col:
        home = vinfo_df[path_col].astype(str).str.extract(r"\[(.*?)\]")[0]
        vsan_count = int(home.isin(vsan).sum())

    info = RvtoolsCapacityInfo(
        total_vms=n,
        fallback_count=fallback,
        vsan_vm_count=vsan_count,
        pre_provisioned_mib=float(sum(prov_orig)),
        post_provisioned_mib=float(sum(new_prov)),
        post_in_use_mib=float(sum(new_inuse)),
    )
    return result, info
