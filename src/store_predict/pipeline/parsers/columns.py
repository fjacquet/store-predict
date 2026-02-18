"""Column alias maps and resolution for normalizing parser output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from store_predict.pipeline.errors import IngestionError

if TYPE_CHECKING:
    import pandas as pd

CANONICAL_COLUMNS: list[str] = [
    "vm_name",
    "os_name",
    "provisioned_mib",
    "in_use_mib",
    "datacenter",
    "cluster",
    "is_template",
    "is_powered_on",
    "source_format",
]

REQUIRED_RVTOOLS_COLUMNS: set[str] = {
    "vm_name",
    "os_name",
    "provisioned_mib",
    "in_use_mib",
}

REQUIRED_LIVEOPTICS_COLUMNS: set[str] = {
    "vm_name",
    "os_name",
    "provisioned_mib",
    "in_use_mib",
}

RVTOOLS_ALIASES: dict[str, list[str]] = {
    "vm_name": ["VM", "VM Name"],
    "powerstate": ["Powerstate", "Power State"],
    "is_template": ["Template"],
    "os_name": [
        "OS according to the VMware Tools",
        "OS according to the configuration file",
    ],
    "provisioned_mib": ["Provisioned MB", "Provisioned MiB"],
    "in_use_mib": ["In Use MB", "In Use MiB"],
    "datacenter": ["Datacenter"],
    "cluster": ["Cluster"],
}

LIVEOPTICS_ALIASES: dict[str, list[str]] = {
    "vm_name": ["VM Name"],
    "os_name": ["VM OS"],
    "provisioned_mib": ["Virtual Disk Size (MiB)"],
    "in_use_mib": ["Guest VM Disk Used (MiB)"],
    "is_template": ["Template"],
    "powerstate": ["Power State"],
    "datacenter": ["Datacenter"],
    "cluster": ["Cluster"],
}


def resolve_columns(
    df: pd.DataFrame,
    aliases: dict[str, list[str]],
    required: set[str],
) -> dict[str, str | None]:
    """Resolve canonical column names to actual DataFrame column names.

    Args:
        df: Source DataFrame whose columns to inspect.
        aliases: Mapping of canonical name to list of known column name variations.
        required: Set of canonical names that must be found or IngestionError is raised.

    Returns:
        Dict mapping canonical_name to actual_column_name (or None if not found
        and not required).

    Raises:
        IngestionError: If any required canonical column cannot be resolved.
    """
    # Strip whitespace from column names (common pitfall with Excel exports)
    df.columns = df.columns.str.strip()

    col_map: dict[str, str | None] = {}
    for canonical, alias_list in aliases.items():
        found: str | None = None
        for alias in alias_list:
            if alias in df.columns:
                found = alias
                break
        col_map[canonical] = found

    # Check required columns are present
    missing = {col for col in required if col_map.get(col) is None}
    if missing:
        available = list(df.columns[:15])
        msg = (
            f"Missing required columns: {sorted(missing)}. "
            f"Available columns (first 15): {available}"
        )
        raise IngestionError(msg)

    return col_map
