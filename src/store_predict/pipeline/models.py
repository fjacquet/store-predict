"""Typed data models for the VM processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FileFormat(Enum):
    """Supported input file formats."""

    RVTOOLS = "rvtools"
    LIVEOPTICS_XLSX = "liveoptics_xlsx"
    LIVEOPTICS_CSV = "liveoptics_csv"
    MERGED = "merged"


@dataclass(frozen=True)
class VMRecord:
    """Normalized VM record from any input format."""

    vm_name: str
    os_name: str
    provisioned_mib: float
    in_use_mib: float
    source_format: FileFormat
    datacenter: str = ""
    cluster: str = ""
    is_template: bool = False
    is_powered_on: bool = True
