"""Tests for pipeline data models."""

import dataclasses

import pytest

from store_predict.pipeline.models import FileFormat, VMRecord


def test_vmrecord_creation() -> None:
    """Create VMRecord with all fields and verify values."""
    vm = VMRecord(
        vm_name="sql-prod-01",
        os_name="Microsoft Windows Server 2022",
        provisioned_mib=102400.0,
        in_use_mib=51200.0,
        source_format=FileFormat.RVTOOLS,
        datacenter="DC1",
        cluster="Cluster-A",
        is_template=False,
        is_powered_on=True,
    )
    assert vm.vm_name == "sql-prod-01"
    assert vm.os_name == "Microsoft Windows Server 2022"
    assert vm.provisioned_mib == 102400.0
    assert vm.in_use_mib == 51200.0
    assert vm.source_format == FileFormat.RVTOOLS
    assert vm.datacenter == "DC1"
    assert vm.cluster == "Cluster-A"
    assert vm.is_template is False
    assert vm.is_powered_on is True


def test_vmrecord_frozen() -> None:
    """Frozen dataclass prevents attribute modification."""
    vm = VMRecord(
        vm_name="test-vm",
        os_name="Linux",
        provisioned_mib=1024.0,
        in_use_mib=512.0,
        source_format=FileFormat.RVTOOLS,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        vm.vm_name = "modified"  # type: ignore[misc]


def test_vmrecord_defaults() -> None:
    """VMRecord with only required fields uses correct defaults."""
    vm = VMRecord(
        vm_name="minimal-vm",
        os_name="Ubuntu 22.04",
        provisioned_mib=2048.0,
        in_use_mib=1024.0,
        source_format=FileFormat.LIVEOPTICS_XLSX,
    )
    assert vm.datacenter == ""
    assert vm.cluster == ""
    assert vm.is_template is False
    assert vm.is_powered_on is True


def test_fileformat_values() -> None:
    """Each FileFormat enum has the expected string value."""
    assert FileFormat.RVTOOLS.value == "rvtools"
    assert FileFormat.LIVEOPTICS_XLSX.value == "liveoptics_xlsx"
    assert FileFormat.LIVEOPTICS_CSV.value == "liveoptics_csv"


def test_vmrecord_equality() -> None:
    """Two identical VMRecords are equal."""
    kwargs = {
        "vm_name": "eq-test",
        "os_name": "CentOS",
        "provisioned_mib": 4096.0,
        "in_use_mib": 2048.0,
        "source_format": FileFormat.LIVEOPTICS_CSV,
    }
    vm1 = VMRecord(**kwargs)
    vm2 = VMRecord(**kwargs)
    assert vm1 == vm2
