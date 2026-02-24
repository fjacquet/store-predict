"""Save and restore a complete StorePredict sizing session as a portable .zip archive."""

from __future__ import annotations

import io
import json
import zipfile

from store_predict.pipeline.errors import IngestionError

SESSION_ZIP_SENTINEL = "session.json"

SCHEMA_VERSION = 1


def save_session_zip(
    session_data: dict[str, object],
    original_file_bytes: bytes,
    original_filename: str,
) -> bytes:
    """Build and return the raw bytes of a .zip archive containing the session.

    The archive contains:
    - The original uploaded file stored at its original_filename path
    - A session.json at the zip root with a JSON snapshot of all session state

    Args:
        session_data: The full app.storage.tab dict containing session state.
        original_file_bytes: Raw bytes of the original uploaded file.
        original_filename: Filename of the original uploaded file (e.g. "rvtools.xlsx").

    Returns:
        Raw bytes of the .zip archive.
    """
    vm_data = session_data.get("vm_data", [])
    if not isinstance(vm_data, list):
        vm_data = []

    snapshot: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "original_filename": original_filename,
        "vm_data": vm_data,
        "project_name": session_data.get("project_name", ""),
        "storage_model": session_data.get("storage_model", "powerstore"),
        "selected_datacenters": session_data.get("selected_datacenters", []),
        "selected_clusters": session_data.get("selected_clusters", []),
        "layout": {
            "max_ds_mib": session_data.get("layout_max_ds_mib", 0.0),
            "max_vms": session_data.get("layout_max_vms", 0),
            "iops_budget": session_data.get("layout_iops_budget", 0.0),
            "snapshot_pct": session_data.get("layout_snapshot_pct", 0.0),
            "growth_pct": session_data.get("layout_growth_pct", 0.0),
        },
        "compute": {
            "preset": session_data.get("compute_preset", ""),
            "overcommit": session_data.get("compute_overcommit", 4.0),
            "vmsc": session_data.get("compute_vmsc", False),
            "ap": session_data.get("compute_ap", False),
            "custom_cps": session_data.get("compute_custom_cps", 0),
            "custom_sockets": session_data.get("compute_custom_sockets", 0),
            "custom_ram": session_data.get("compute_custom_ram", 0),
            "vmsc_split": session_data.get("compute_vmsc_split", 50),
            "ap_active": session_data.get("compute_ap_active", 100),
        },
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(SESSION_ZIP_SENTINEL, json.dumps(snapshot, ensure_ascii=False))
        zf.writestr(original_filename, original_file_bytes)

    return buf.getvalue()


def is_session_zip(content: bytes) -> bool:
    """Return True if content is a valid ZIP containing a session.json at root.

    This distinguishes StorePredict session archives from LiveOptics .zip files,
    which never contain a session.json.

    Args:
        content: Raw bytes to inspect.

    Returns:
        True if the content is a StorePredict session archive, False otherwise.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return SESSION_ZIP_SENTINEL in zf.namelist()
    except Exception:
        return False


def restore_session_zip(content: bytes) -> dict[str, object]:
    """Read a session .zip archive and return a flat dict of app.storage.tab keys.

    The returned dict is ready to be written back to app.storage.tab to restore
    a session. Special keys prefixed with '_restored_' carry the original file
    bytes and filename for the upload page to reconstruct the format hint.

    Args:
        content: Raw bytes of a StorePredict session archive.

    Returns:
        Flat dict of app.storage.tab keys with all session state.

    Raises:
        IngestionError: If the archive is invalid, session.json is missing,
            JSON cannot be parsed, or schema_version != 1.
    """
    try:
        zf_buf = io.BytesIO(content)
        with zipfile.ZipFile(zf_buf) as zf:
            names = zf.namelist()
            if SESSION_ZIP_SENTINEL not in names:
                raise IngestionError(
                    "Invalid session archive: session.json not found",
                    details=f"Archive contains: {names}",
                )
            raw_json = zf.read(SESSION_ZIP_SENTINEL)
            snapshot = json.loads(raw_json)
            schema_version = snapshot.get("schema_version")
            if schema_version != SCHEMA_VERSION:
                raise IngestionError(
                    f"Unsupported session archive version: {schema_version}",
                    details=f"Expected schema_version={SCHEMA_VERSION}",
                )
            original_filename: str = snapshot.get("original_filename", "")
            original_bytes = b""
            if original_filename and original_filename in names:
                original_bytes = zf.read(original_filename)

    except IngestionError:
        raise
    except zipfile.BadZipFile as exc:
        raise IngestionError(
            "Invalid session archive: not a valid ZIP file",
            details=str(exc),
        ) from exc
    except json.JSONDecodeError as exc:
        raise IngestionError(
            "Invalid session archive: session.json is not valid JSON",
            details=str(exc),
        ) from exc
    except Exception as exc:
        raise IngestionError(
            "Failed to restore session archive",
            details=str(exc),
        ) from exc

    layout: dict[str, float | int] = snapshot.get("layout") or {}
    compute: dict[str, float | int | bool | str] = snapshot.get("compute") or {}

    result: dict[str, object] = {
        "vm_data": snapshot.get("vm_data", []),
        "project_name": snapshot.get("project_name", ""),
        "storage_model": snapshot.get("storage_model", "powerstore"),
        "selected_datacenters": snapshot.get("selected_datacenters", []),
        "selected_clusters": snapshot.get("selected_clusters", []),
        # Layout keys
        "layout_max_ds_mib": float(layout.get("max_ds_mib", 0.0)),
        "layout_max_vms": int(layout.get("max_vms", 0)),
        "layout_iops_budget": float(layout.get("iops_budget", 0.0)),
        "layout_snapshot_pct": float(layout.get("snapshot_pct", 0.0)),
        "layout_growth_pct": float(layout.get("growth_pct", 0.0)),
        # Compute keys
        "compute_preset": str(compute.get("preset", "")),
        "compute_overcommit": float(compute.get("overcommit", 4.0)),
        "compute_vmsc": bool(compute.get("vmsc", False)),
        "compute_ap": bool(compute.get("ap", False)),
        "compute_custom_cps": int(compute.get("custom_cps", 0)),
        "compute_custom_sockets": int(compute.get("custom_sockets", 0)),
        "compute_custom_ram": int(compute.get("custom_ram", 0)),
        "compute_vmsc_split": int(compute.get("vmsc_split", 50)),
        "compute_ap_active": int(compute.get("ap_active", 100)),
        # Restoration metadata
        "_restored_original_filename": original_filename,
        "_restored_original_bytes": original_bytes,
    }

    return result
